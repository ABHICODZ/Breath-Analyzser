#!/usr/bin/env python3
"""
===========================================================================
 VAYU DRISHTI — BLIND STATION VALIDATION (Leave-One-Out Live Test)
===========================================================================
 How it works:
   1. Uses the EXACT 40 stations from app/core/stations.py (single source of truth)
   2. Fetches LIVE µg/m³ readings from OpenAQ v3 (NOT WAQI)
   3. For each station with valid data:
      - HIDES it (treats it as an unknown blind zone)
      - Uses all OTHER stations as anchor inputs
      - Runs the ML engine (TemporalSpatialNet or IDW fallback) to PREDICT
      - Compares the prediction against the REAL reading
   4. Reports per-station and overall accuracy

 DATA INTEGRITY:
   - ONLY real live data from OpenAQ is used. 
   - NO fabricated/estimated/placeholder values.
   - If OpenAQ rate-limits, the test stops cleanly.

 Usage:
   python test_blind_station.py
===========================================================================
"""

import sys
import os
import math
import time
from datetime import datetime

# ─── Add backend to path ──────────────────────────────────────────────────────
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# ─── Import from single source of truth ───────────────────────────────────────
from app.core.stations import STATION_COORDS, DELHI_CENTER
from app.services.openaq_client import (
    OpenAQClient,
    OpenAQRateLimitError,
    OpenAQDataUnavailableError,
)

# ─── ANSI Colors ───────────────────────────────────────────────────────────────
class C:
    G  = '\033[92m'   # Green
    R  = '\033[91m'   # Red
    Y  = '\033[93m'   # Yellow
    B  = '\033[94m'   # Blue
    W  = '\033[97m'   # White
    D  = '\033[90m'   # Dim
    BLD = '\033[1m'
    RST = '\033[0m'


# ─── Step 1: Fetch Live Data from OpenAQ ──────────────────────────────────────

def fetch_live_stations():
    """
    Queries OpenAQ v3 for each station in STATION_COORDS.
    Returns real µg/m³ concentration values.
    
    STRICT: No fabricated values. If OpenAQ has no data for a station,
    that station is skipped (not filled with defaults).
    """
    print(f"\n{C.BLD}{C.B}{'='*72}{C.RST}")
    print(f"{C.BLD}{C.B}{'STEP 1: FETCHING LIVE DATA FROM OPENAQ':^72}{C.RST}")
    print(f"{C.BLD}{C.B}{'='*72}{C.RST}\n")

    print(f"  {C.BLD}Station source:{C.RST}  app/core/stations.py → STATION_COORDS")
    print(f"  {C.BLD}Data source:{C.RST}     OpenAQ v3 API (µg/m³ concentrations)")
    print(f"  {C.BLD}Total stations:{C.RST}   {len(STATION_COORDS)}")
    print(f"  {C.D}  Discovering OpenAQ location IDs...{C.RST}\n")

    client = OpenAQClient()

    # Phase 1: Discover location IDs
    try:
        discovered = client.discover_station_ids(STATION_COORDS)
        print(f"\n  {C.G}✓ Discovered {len(discovered)} OpenAQ locations{C.RST}\n")
    except OpenAQRateLimitError as e:
        print(f"\n  {C.R}✗ OpenAQ API rate limit reached during discovery.{C.RST}")
        print(f"  {C.R}  Live data is temporarily unavailable.{C.RST}")
        print(f"  {C.R}  Error: {e}{C.RST}")
        return []

    # Phase 2: Fetch latest readings
    print(f"  {C.D}  Fetching latest readings for each station...{C.RST}\n")

    detailed_stations = []
    skipped_no_data = []

    for name, (lat, lon) in STATION_COORDS.items():
        loc_id = discovered.get(name)
        if loc_id is None:
            print(f"  {C.D}  ─ {name:36s} │ No OpenAQ location found — skipped{C.RST}")
            skipped_no_data.append(name)
            continue

        try:
            reading = client.fetch_latest_for_station(name, lat, lon, loc_id)
            if reading is None:
                print(f"  {C.D}  ─ {name:36s} │ No valid PM2.5 data — skipped{C.RST}")
                skipped_no_data.append(name)
                continue

            entry = {
                "name":    reading.name,
                "lat":     reading.lat,
                "lon":     reading.lon,
                "pm25":    reading.pm25,
                "pm10":    reading.pm10 or 0,
                "no2":     reading.no2 or 0,
                "so2":     reading.so2 or 0,
                "co_ppb":  reading.co or 0,
                "timestamp": reading.timestamp,
            }
            detailed_stations.append(entry)
            print(
                f"  {C.G}✓{C.RST} {name:36s} │ "
                f"PM2.5: {entry['pm25']:>6.1f} µg/m³ │ "
                f"PM10: {str(round(entry['pm10'], 1)):>6} │ "
                f"NO2: {str(round(entry['no2'], 1)):>5}"
            )

        except OpenAQRateLimitError as e:
            print(f"\n  {C.R}✗ OpenAQ rate limit hit at station '{name}'.{C.RST}")
            print(f"  {C.R}  Stopping data fetch. Got {len(detailed_stations)} stations so far.{C.RST}")
            break
        except Exception as e:
            print(f"  {C.R}✗{C.RST} {name:36s} │ Error: {e}")
            skipped_no_data.append(name)

    print(f"\n  {C.BLD}Fetch Summary:{C.RST}")
    print(f"    Stations in STATION_COORDS:   {len(STATION_COORDS)}")
    print(f"    With valid OpenAQ data:       {C.G}{len(detailed_stations)}{C.RST}")
    print(f"    Skipped (no data):            {len(skipped_no_data)}")
    coverage = len(detailed_stations) / len(STATION_COORDS) * 100 if STATION_COORDS else 0
    print(f"    {C.BLD}Coverage:{C.RST}                   {coverage:.0f}%")

    return detailed_stations


# ─── Step 2: Import the ML Engine ─────────────────────────────────────────────

def get_ml_engine():
    """Import and instantiate the production ML engine."""
    from app.services.ml_engine import TemporalNeuralNetworkMock
    engine = TemporalNeuralNetworkMock()
    return engine


# ─── Step 3: Leave-One-Out Blind Test ─────────────────────────────────────────

def run_blind_test(stations, engine):
    """
    For each station:
      1. Remove it from the anchor set (blind it)
      2. Predict its PM2.5 using the remaining stations
      3. Compare prediction vs actual
    """
    print(f"\n{C.BLD}{C.B}{'='*72}{C.RST}")
    print(f"{C.BLD}{C.B}{'STEP 2: LEAVE-ONE-OUT BLIND STATION VALIDATION':^72}{C.RST}")
    print(f"{C.BLD}{C.B}{'='*72}{C.RST}\n")

    if len(stations) < 3:
        print(f"{C.R}  Need at least 3 stations for blind testing. Got {len(stations)}.{C.RST}")
        return []

    model_type = "TemporalSpatialNet (MLP)" if engine.use_torch else "IDW Fallback (Physics-based)"
    print(f"  {C.BLD}Inference Engine:{C.RST}  {model_type}")
    print(f"  {C.BLD}Anchor Stations:{C.RST}   {len(stations)}")
    print(f"  {C.BLD}Tests to Run:{C.RST}      {len(stations)} (one per station)\n")

    print(f"  {'#':<3} {'Station':<36} │ {'Actual':>8} │ {'Predicted':>9} │ {'Error':>7} │ {'Error%':>7} │ {'Grade'}")
    print(f"  {'─'*3} {'─'*36}─┼─{'─'*8}─┼─{'─'*9}─┼─{'─'*7}─┼─{'─'*7}─┼─{'─'*12}")

    results = []

    for i, blind_station in enumerate(stations):
        # Build anchor set (all stations EXCEPT the blind one)
        anchors = []
        for j, s in enumerate(stations):
            if j == i:
                continue
            anchors.append({
                "id":      str(j),
                "name":    s["name"],
                "lat":     s["lat"],
                "lon":     s["lon"],
                "pm25":    s["pm25"],
                "pm10":    s.get("pm10", 0) or 0,
                "no2":     s.get("no2", 0)  or 0,
                "so2":     s.get("so2", 0)  or 0,
                "co_ppb":  s.get("co_ppb", 0) or 0,
            })

        blind_ward = {
            "id":   f"blind_{i}",
            "name": blind_station["name"],
            "lat":  blind_station["lat"],
            "lon":  blind_station["lon"],
        }

        # Run prediction
        predictions = engine.predict(anchors, [blind_ward])
        pred_data = predictions.get(f"blind_{i}", {})
        predicted_pm25 = pred_data.get("pm25", 0)
        actual_pm25 = blind_station["pm25"]

        if actual_pm25 is None or actual_pm25 == 0:
            continue

        abs_error = abs(predicted_pm25 - actual_pm25)
        pct_error = (abs_error / actual_pm25) * 100 if actual_pm25 > 0 else 0

        if pct_error < 10:
            grade = f"{C.G}EXCELLENT{C.RST}"
            grade_tag = "EXCELLENT"
        elif pct_error < 20:
            grade = f"{C.G}VERY GOOD{C.RST}"
            grade_tag = "VERY GOOD"
        elif pct_error < 30:
            grade = f"{C.G}GOOD{C.RST}"
            grade_tag = "GOOD"
        elif pct_error < 50:
            grade = f"{C.Y}MODERATE{C.RST}"
            grade_tag = "MODERATE"
        else:
            grade = f"{C.R}POOR{C.RST}"
            grade_tag = "POOR"

        idx = len(results) + 1
        print(f"  {idx:<3} {blind_station['name']:<36} │ {actual_pm25:>8.1f} │ {predicted_pm25:>9.1f} │ {abs_error:>7.1f} │ {pct_error:>6.1f}% │ {grade}")

        results.append({
            "name": blind_station["name"],
            "actual": actual_pm25,
            "predicted": predicted_pm25,
            "abs_error": abs_error,
            "pct_error": pct_error,
            "grade": grade_tag,
        })

    return results


# ─── Step 4: Summary Report ───────────────────────────────────────────────────

def print_summary(results, engine, total_defined):
    if not results:
        print(f"\n{C.R}  No valid results to summarize.{C.RST}")
        return

    print(f"\n{C.BLD}{C.B}{'='*72}{C.RST}")
    print(f"{C.BLD}{C.B}{'VALIDATION SUMMARY':^72}{C.RST}")
    print(f"{C.BLD}{C.B}{'='*72}{C.RST}\n")

    n = len(results)
    avg_abs  = sum(r["abs_error"] for r in results) / n
    avg_pct  = sum(r["pct_error"] for r in results) / n
    sorted_pct = sorted(r["pct_error"] for r in results)
    median_pct = sorted_pct[n // 2]
    max_err  = max(results, key=lambda r: r["pct_error"])
    min_err  = min(results, key=lambda r: r["pct_error"])

    grade_counts = {}
    for r in results:
        grade_counts[r["grade"]] = grade_counts.get(r["grade"], 0) + 1

    within_10 = sum(1 for r in results if r["pct_error"] < 10)
    within_20 = sum(1 for r in results if r["pct_error"] < 20)
    within_30 = sum(1 for r in results if r["pct_error"] < 30)
    within_50 = sum(1 for r in results if r["pct_error"] < 50)

    model_type = "TemporalSpatialNet (MLP)" if engine.use_torch else "IDW + Wind Advection (Physics Fallback)"

    print(f"  {C.BLD}Inference Engine:{C.RST}     {model_type}")
    print(f"  {C.BLD}Data Source:{C.RST}          OpenAQ v3 (µg/m³ concentrations)")
    print(f"  {C.BLD}Station Source:{C.RST}       app/core/stations.py ({total_defined} defined)")
    print(f"  {C.BLD}Stations Tested:{C.RST}      {n} / {total_defined} ({n/total_defined*100:.0f}% coverage)")
    print(f"  {C.BLD}Timestamp:{C.RST}            {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print()
    print(f"  {C.BLD}Mean Absolute Error:{C.RST}  {avg_abs:.1f} µg/m³")
    print(f"  {C.BLD}Mean % Error:{C.RST}         {avg_pct:.1f}%")
    print(f"  {C.BLD}Median % Error:{C.RST}       {median_pct:.1f}%")
    print(f"  {C.BLD}Best Station:{C.RST}         {min_err['name']} ({min_err['pct_error']:.1f}% error)")
    print(f"  {C.BLD}Worst Station:{C.RST}        {max_err['name']} ({max_err['pct_error']:.1f}% error)")

    print(f"\n  {C.BLD}Accuracy Tiers:{C.RST}")
    print(f"    Within 10%:  {within_10}/{n} stations ({within_10/n*100:.0f}%)")
    print(f"    Within 20%:  {within_20}/{n} stations ({within_20/n*100:.0f}%)")
    print(f"    Within 30%:  {within_30}/{n} stations ({within_30/n*100:.0f}%)")
    print(f"    Within 50%:  {within_50}/{n} stations ({within_50/n*100:.0f}%)")

    print(f"\n  {C.BLD}Grade Distribution:{C.RST}")
    for grade in ["EXCELLENT", "VERY GOOD", "GOOD", "MODERATE", "POOR"]:
        count = grade_counts.get(grade, 0)
        bar = "█" * count + "░" * (n - count)
        if grade in ("EXCELLENT", "VERY GOOD", "GOOD"):
            color = C.G
        elif grade == "MODERATE":
            color = C.Y
        else:
            color = C.R
        print(f"    {color}{grade:<12}{C.RST}  {bar}  {count}")

    print(f"\n  {C.BLD}{'─'*60}{C.RST}")
    if avg_pct < 20:
        print(f"  {C.G}{C.BLD}✓ SYSTEM PERFORMING EXCELLENTLY (avg error < 20%){C.RST}")
    elif avg_pct < 30:
        print(f"  {C.G}{C.BLD}✓ SYSTEM PERFORMING WELL (avg error < 30%){C.RST}")
    elif avg_pct < 50:
        print(f"  {C.Y}{C.BLD}⚠ SYSTEM PERFORMING ADEQUATELY (avg error < 50%){C.RST}")
    else:
        print(f"  {C.R}{C.BLD}✗ SYSTEM NEEDS IMPROVEMENT (avg error ≥ 50%){C.RST}")

    if not engine.use_torch:
        print(f"\n  {C.Y}{C.BLD}NOTE:{C.RST} {C.Y}The neural network weights are NOT loaded.{C.RST}")
        print(f"  {C.Y}Results above are from the IDW physics fallback only.{C.RST}")
        print(f"  {C.Y}To test the actual MLP, train and deploy the weights first.{C.RST}")

    print(f"\n{C.BLD}{C.B}{'='*72}{C.RST}")


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{C.BLD}{C.W}╔══════════════════════════════════════════════════════════════════════╗{C.RST}")
    print(f"{C.BLD}{C.W}║     VAYU DRISHTI — BLIND STATION VALIDATION (Live Leave-One-Out)    ║{C.RST}")
    print(f"{C.BLD}{C.W}╚══════════════════════════════════════════════════════════════════════╝{C.RST}")
    print(f"\n  {C.D}Data source: OpenAQ v3 │ Stations: app/core/stations.py ({len(STATION_COORDS)} stations){C.RST}")
    print(f"  {C.D}For each: fetch µg/m³ → blind it → predict → compare{C.RST}")

    # 1. Fetch live data
    stations = fetch_live_stations()
    if not stations:
        print(f"\n{C.R}ABORTED: No live station data available from OpenAQ.{C.RST}")
        sys.exit(1)

    stations = [s for s in stations if s.get("pm25") is not None and s["pm25"] > 0]
    print(f"\n  {C.BLD}Stations ready for blind testing:{C.RST} {len(stations)} / {len(STATION_COORDS)}")

    if len(stations) < 3:
        print(f"\n{C.R}ABORTED: Need at least 3 stations with PM2.5 data.{C.RST}")
        sys.exit(1)

    # 2. Load the ML engine
    print(f"\n{C.BLD}{C.B}{'='*72}{C.RST}")
    print(f"{C.BLD}{C.B}{'LOADING ML ENGINE':^72}{C.RST}")
    print(f"{C.BLD}{C.B}{'='*72}{C.RST}\n")
    engine = get_ml_engine()

    # 3. Run blind test
    results = run_blind_test(stations, engine)

    # 4. Summary
    print_summary(results, engine, total_defined=len(STATION_COORDS))


if __name__ == "__main__":
    try:
        main()
    except OpenAQRateLimitError as e:
        print(f"\n\n{C.R}  OpenAQ API rate limit reached. Live data is temporarily unavailable.{C.RST}")
        print(f"  {C.R}  Error: {e}{C.RST}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n{C.Y}  Interrupted by user.{C.RST}")
        sys.exit(0)
