from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import math
import httpx
import json
import os
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ─── Models ───────────────────────────────────────────────────────────────────

class WardStat(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    aqi: int
    pm25: float
    dominant_source: str
    status: str
    trend: str

class Recommendation(BaseModel):
    id: str
    ward: str
    issue: str
    action: str
    impact: str
    urgency: str

# ─── Config ──────────────────────────────────────────────────────────────────

# [DEPRECATED: WAQI] — The following WAQI configuration was removed on 2026-06-15.
# WAQI returned AQI index values, not real µg/m³ concentrations. The system now
# uses OpenAQ v3 which provides actual µg/m³ readings from CPCB sensors.
#
# OLD CODE:
# WAQI_TOKEN = os.environ.get("WAQI_TOKEN")
# if not WAQI_TOKEN:
#     print("[FATAL] WAQI_TOKEN environment variable is missing.")
# WAQI_BOUNDS_URL = f"https://api.waqi.info/map/bounds/?latlng=28.4,76.8,28.9,77.4&token={WAQI_TOKEN}"

# --- OpenAQ Configuration (Active) ---
from app.core.stations import STATION_COORDS, DELHI_CENTER
from app.services.openaq_client import (
    openaq_client,
    OpenAQRateLimitError,
    OpenAQDataUnavailableError,
)

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_LOCATION   = os.environ.get("GCP_LOCATION", "us-central1")

# Auto-detect project ID from the service account credentials file if not set via env var
# This handles the case where no .env file exists (e.g., local Windows development)
_CREDS_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'services', 'ee-credentials.json')
if not GCP_PROJECT_ID and os.path.exists(_CREDS_PATH):
    try:
        import json as _json
        _creds = _json.load(open(_CREDS_PATH))
        GCP_PROJECT_ID = _creds.get("project_id")
        if GCP_PROJECT_ID:
            print(f"[GCP] Auto-detected project_id='{GCP_PROJECT_ID}' from ee-credentials.json")
        else:
            print("[GCP] ee-credentials.json has no project_id field")
    except Exception as _e:
        print(f"[GCP] Failed to read credentials for project_id: {_e}")

if not GCP_PROJECT_ID:
    print("[FATAL] GCP_PROJECT_ID not set and could not be read from credentials. Vertex AI will fail.")
else:
    print(f"[GCP] Project: {GCP_PROJECT_ID} | Location: {GCP_LOCATION}")

# ─── Utility Functions ─────────────────────────────────────────────────────────

def load_geojson(filename: str) -> list:
    data_list = []
    # Look in backend/app/data/ directory
    path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', filename)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for idx, feat in enumerate(data.get('features', [])):
                    props = feat.get('properties', {})
                    coords = feat.get('geometry', {}).get('coordinates', [None, None])
                    # GeoJSON coords are [lon, lat]
                    lon_val = coords[0] if isinstance(coords, list) and len(coords) >= 2 else None
                    lat_val = coords[1] if isinstance(coords, list) and len(coords) >= 2 else None
                    safe_id = str(props.get('ward_no') or props.get('name') or f"W_{idx}")
                    safe_name = str(props.get('name') or props.get('ward_name') or props.get('ward_no') or f'Ward {idx}').title()
                    data_list.append({
                        "id": safe_id,
                        "name": safe_name,
                        "lat": float(props.get('lat', lat_val or 28.6)),
                        "lon": float(props.get('lon', lon_val or 77.2)),
                    })
        except Exception as e:
            print(f"[GeoJSON] Failed to parse {filename}: {e}")
    return data_list

def get_status(aqi: int) -> str:
    if aqi <= 50:  return "Good"
    if aqi <= 100: return "Moderate"
    if aqi <= 150: return "Unhealthy (SG)"
    if aqi <= 200: return "Unhealthy"
    if aqi <= 300: return "Very Unhealthy"
    return "Hazardous"

def pm25_to_aqi_us(pm25: float) -> int:
    """Official US EPA AQI breakpoints for PM2.5 (µg/m³)."""
    bp = [
        (0.0,   12.0,  0,   50),
        (12.1,  35.4,  51,  100),
        (35.5,  55.4,  101, 150),
        (55.5,  150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]
    for c_lo, c_hi, i_lo, i_hi in bp:
        if c_lo <= pm25 <= c_hi:
            return round(i_lo + (pm25 - c_lo) * (i_hi - i_lo) / (c_hi - c_lo))
    return 500 if pm25 > 500.4 else 0

# [DEPRECATED: WAQI] — aqi_us_to_pm25() was needed to reverse-map WAQI's AQI index
# values back to µg/m³. OpenAQ returns real µg/m³ directly, so this is no longer needed.
#
# def aqi_us_to_pm25(aqi: int) -> float:
#     """Reverse-map US EPA AQI → PM2.5 µg/m³ (WAQI reports US AQI)."""
#     bp = [
#         (0,   50,  0.0,   12.0),
#         (51,  100, 12.1,  35.4),
#         (101, 150, 35.5,  55.4),
#         (151, 200, 55.5,  150.4),
#         (201, 300, 150.5, 250.4),
#         (301, 400, 250.5, 350.4),
#         (401, 500, 350.5, 500.4),
#     ]
#     for i_lo, i_hi, c_lo, c_hi in bp:
#         if i_lo <= aqi <= i_hi:
#             return c_lo + (aqi - i_lo) * (c_hi - c_lo) / (i_hi - i_lo)
#     return 250.0

def detect_source(pm25: float, pm10: float, no2: float, co: float, so2: float) -> str:
    """Classify dominant pollution source from atmospheric chemistry."""
    if so2 > 10 and pm25 > 80:
        return "Industrial SO₂ Emissions"
    if no2 > 35 or co > 800:
        return "Vehicle Exhaust & Heavy Traffic"
    if pm10 > 0 and pm25 > 0 and pm10 > (pm25 * 2.2):
        return "Construction & Road Dust"
    if pm25 > 120:
        return "Biomass / Stubble Burning"
    return "Mixed Urban Emissions"

def nearest_anchor(ward_lat: float, ward_lon: float, anchors: list) -> dict | None:
    """Find the closest real station to a given ward by Euclidean distance."""
    if not anchors:
        return None
    return min(anchors, key=lambda a: math.hypot(ward_lat - a['lat'], ward_lon - a['lon']))

# ─── ML Engine ────────────────────────────────────────────────────────────────

from app.services.ml_engine import TemporalNeuralNetworkMock
ML_ENGINE = TemporalNeuralNetworkMock()
INFERENCE_GRID_CACHE: dict = {"timestamp": 0.0, "data": [], "anchors": [], "error": None}
BACKGROUND_TASK_STARTED = False

# Cached ward metadata
WARD_META = load_geojson('kaggle_wards.geojson')
DISTRICT_META = load_geojson('delhi_wards.geojson')

# ─── OpenAQ Station Anchor Fetcher (Replaces WAQI) ────────────────────────────

def fetch_openaq_station_anchors() -> list:
    """
    Fetch real-time µg/m³ readings from OpenAQ for all 40 CPCB stations.
    
    Returns list of anchor dicts compatible with the ML engine's predict() method.
    
    STRICT DATA INTEGRITY:
      - Only returns stations with valid PM2.5 data from OpenAQ.
      - NEVER injects fabricated/default/estimated values.
      - If OpenAQ returns no data, the anchor list will be shorter (not padded).
      - If rate limited, raises OpenAQRateLimitError (caller must handle).
    """
    try:
        readings, failed, error_msg = openaq_client.fetch_all_latest(STATION_COORDS)
    except OpenAQRateLimitError as e:
        logger.error(f"[OpenAQ Anchors] {e}")
        raise
    except OpenAQDataUnavailableError as e:
        logger.error(f"[OpenAQ Anchors] {e}")
        return []

    if not readings:
        logger.error(
            "[OpenAQ Anchors] No stations returned valid data. "
            "The inference grid will have NO anchors."
        )
        return []

    anchors = []
    for r in readings:
        pm25 = r.pm25
        aqi = pm25_to_aqi_us(pm25)
        anchors.append({
            "id": str(r.openaq_location_id),
            "name": r.name,
            "lat": r.lat,
            "lon": r.lon,
            "aqi": aqi,
            "pm25": round(pm25, 1),
            "pm10": r.pm10 or 0.0,
            "no2": r.no2 or 0.0,
            "so2": r.so2 or 0.0,
            "co_ppb": r.co or 0.0,
            "dominant_source": detect_source(
                pm25, r.pm10 or 0, r.no2 or 0, r.co or 0, r.so2 or 0
            ),
            "status": get_status(aqi),
            "trend": "stable",
        })

    if error_msg:
        logger.warning(f"[OpenAQ Anchors] Partial data: {error_msg}")

    print(f"[OpenAQ] Loaded {len(anchors)} real monitoring stations with µg/m³ data.")
    return anchors


# [DEPRECATED: WAQI] — The old WAQI anchor fetcher is preserved below for reference.
# It used the WAQI bounds API which returned US AQI index values, not µg/m³.
# These had to be reverse-mapped via aqi_us_to_pm25(), introducing estimation error.
#
# async def fetch_real_station_anchors(client: httpx.AsyncClient) -> list:
#     """
#     [DEPRECATED] Fetch all real CPCB/WAQI monitoring stations in Delhi NCR via bounds API.
#     Returns list of anchor dicts with real PM2.5 values on India CPCB scale.
#     """
#     try:
#         res = await client.get(WAQI_BOUNDS_URL, timeout=15.0)
#         stations = res.json().get("data", [])
#         anchors = []
#         for s in stations:
#             try:
#                 aqi_us = int(s.get("aqi", 0))
#             except (ValueError, TypeError):
#                 continue
#             if aqi_us <= 0:
#                 continue
#             pm25 = aqi_us_to_pm25(aqi_us)
#             aqi_us = pm25_to_aqi_us(pm25)
#             anchors.append({
#                 "id": str(s.get("uid", "")),
#                 "name": s["station"]["name"].split(",")[0].strip(),
#                 "lat": float(s["lat"]),
#                 "lon": float(s["lon"]),
#                 "aqi": aqi_us,
#                 "pm25": round(float(pm25), 1),
#                 "dominant_source": "Live CPCB/WAQI Station",
#                 "status": get_status(aqi_us),
#                 "trend": "stable",
#             })
#         print(f"[WAQI] Loaded {len(anchors)} real monitoring stations.")
#         return anchors
#     except Exception as e:
#         print(f"[WAQI BOUNDS] Error: {e}")
#         return []


# ─── Chemistry Enrichment (Open-Meteo, uses real anchor as PM2.5 base) ────────

async def enrich_with_open_meteo(client: httpx.AsyncClient, ward: dict, base_pm25: float) -> WardStat:
    """
    Try to get atmospheric chemistry from Open-Meteo.
    PM2.5 base is already anchored from the nearest real OpenAQ station.
    Open-Meteo only enriches source classification; we don't override PM2.5 from it
    (Open-Meteo PM2.5 is a forecast model, not a real measurement).
    """
    pm25 = base_pm25
    pm10, no2, co, so2 = 0.0, 0.0, 0.0, 0.0
    try:
        url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={ward['lat']}&longitude={ward['lon']}"
            f"&current=pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide"
        )
        r = await client.get(url, timeout=8.0)
        if r.status_code == 200:
            c = r.json().get('current', {})
            pm10 = c.get('pm10', 0.0) or 0.0
            no2  = c.get('nitrogen_dioxide', 0.0) or 0.0
            co   = c.get('carbon_monoxide', 0.0) or 0.0
            so2  = c.get('sulphur_dioxide', 0.0) or 0.0
    except Exception:
        pass

    aqi = pm25_to_aqi_us(pm25)
    return WardStat(
        id=ward["id"],
        name=ward["name"],
        lat=ward["lat"],
        lon=ward["lon"],
        aqi=aqi,
        pm25=round(pm25, 1),
        dominant_source=detect_source(pm25, pm10, no2, co, so2),
        status=get_status(aqi),
        trend="stable",
    )

# ─── Background ML Inference Loop ─────────────────────────────────────────────

async def _autonomous_ml_inference_loop():
    print("[TNN] Autonomous Spatial ML Loop Started (OpenAQ data source).")

    # Discover OpenAQ location IDs once at startup
    try:
        openaq_client.discover_station_ids(STATION_COORDS)
        print(f"[TNN] OpenAQ station discovery complete: {len(openaq_client._station_id_cache)} stations mapped.")
    except OpenAQRateLimitError as e:
        print(f"[TNN] OpenAQ rate limit during station discovery: {e}")
        print("[TNN] Will retry discovery on next cycle.")
    except Exception as e:
        print(f"[TNN] Station discovery error (will retry): {e}")

    while True:
        try:
            anchors = fetch_openaq_station_anchors()

            if not anchors:
                INFERENCE_GRID_CACHE["error"] = (
                    "OpenAQ returned no valid station data. "
                    "Live air quality data is temporarily unavailable."
                )
                print("[TNN] OpenAQ anchor fetch returned 0 stations — skipping cycle.")
                await asyncio.sleep(60)
                continue

            # Clear any previous error state
            INFERENCE_GRID_CACHE["error"] = None

            # Store anchors in cache for district view to reuse
            INFERENCE_GRID_CACHE["anchors"] = anchors

            # Use the ML engine to interpolate all wards
            inferences = ML_ENGINE.predict(anchors, WARD_META)
            results = list(inferences.values())
            results.sort(key=lambda x: x['aqi'], reverse=True)

            INFERENCE_GRID_CACHE["data"] = results
            INFERENCE_GRID_CACHE["timestamp"] = time.time()
            print(f"[TNN] Inferred {len(results)} ward zones from {len(anchors)} OpenAQ anchor stations.")

        except OpenAQRateLimitError as e:
            INFERENCE_GRID_CACHE["error"] = str(e)
            print(f"[TNN] OpenAQ rate limit: {e}. Will retry in 120s.")
            await asyncio.sleep(120)  # Longer wait on rate limit
            continue
        except Exception as e:
            INFERENCE_GRID_CACHE["error"] = f"Inference loop error: {e}"
            print(f"[TNN FATAL] Inference loop error: {e}")

        await asyncio.sleep(300)  # Refresh every 5 minutes

# ─── API Endpoints ─────────────────────────────────────────────────────────────

@router.get("/wards", response_model=List[WardStat])
async def get_ward_stats(level: str = 'ward'):
    """
    Returns live AQI data.
    - level=ward    → interpolated wards (TNN ML inference from OpenAQ anchors)
    - level=district → real OpenAQ station readings grouped by district proximity
    """
    global BACKGROUND_TASK_STARTED
    if not BACKGROUND_TASK_STARTED:
        asyncio.create_task(_autonomous_ml_inference_loop())
        BACKGROUND_TASK_STARTED = True

    # Wait up to 30s for first ML cycle to complete
    for _ in range(300):
        if INFERENCE_GRID_CACHE["data"]:
            break
        await asyncio.sleep(0.1)

    # Check for error state — surface it explicitly, never mask it
    if INFERENCE_GRID_CACHE.get("error") and not INFERENCE_GRID_CACHE["data"]:
        raise HTTPException(
            status_code=503,
            detail=INFERENCE_GRID_CACHE["error"]
        )

    if level == 'district':
        anchors = INFERENCE_GRID_CACHE.get("anchors", [])
        if not anchors:
            raise HTTPException(
                status_code=503,
                detail="No OpenAQ station data available for district view."
            )

        district_results = []
        for dist in DISTRICT_META:
            closest = nearest_anchor(dist['lat'], dist['lon'], anchors)
            if closest:
                district_results.append(WardStat(**{
                    "id": dist["id"],
                    "name": dist["name"],
                    "lat": dist["lat"],
                    "lon": dist["lon"],
                    "aqi": closest["aqi"],
                    "pm25": closest["pm25"],
                    "dominant_source": f"Nearest Sensor: {closest['name']}",
                    "status": closest["status"],
                    "trend": "stable"
                }))
        return district_results

    # Ward mode: return TNN ML-inferred grid
    return [WardStat(**w) for w in INFERENCE_GRID_CACHE["data"]] if INFERENCE_GRID_CACHE["data"] else []


@router.get("/recommendations", response_model=List[Recommendation])
async def get_policy_recommendations():
    """
    Generates real-time policy recommendations via Google Gemini 1.5 Pro.
    AI calls are fully logged and monitored for repetition (reliability guard).
    """
    import re, hashlib
    # Fix the async race condition: Wait up to 30s for ML cycle to populate cache
    for _ in range(300):
        if INFERENCE_GRID_CACHE.get("data"):
            break
        await asyncio.sleep(0.1)

    bad_zones = INFERENCE_GRID_CACHE.get("data", [])[:5]

    try:
        if not bad_zones:
            raise ValueError("No inference data available yet — ML inference grid is empty")

        hotspot_text = "\n".join(
            f"- {z['name']}: AQI {z['aqi']} (PM2.5: {z['pm25']} µg/m³, Source: {z['dominant_source']})"
            for z in bad_zones
        )
        prompt = (
            "You are the Chief Environmental Officer of Delhi Municipal Corporation.\n"
            "The following are the top 5 real-time AQI hotspots right now:\n"
            f"{hotspot_text}\n\n"
            "Generate exactly 3 precise, actionable policy interventions.\n"
            "Output ONLY a raw JSON array (no markdown, no explanation):\n"
            '[{"id":"REC-1","ward":"<zone>","issue":"<1 sentence>","action":"<1 sentence>","impact":"<1 sentence>","urgency":"Critical|High|Medium"}]'
        )

        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        ai_start = time.time()
        print(f"[AI] Gemini request starting | prompt_hash={prompt_hash} | hotspots={len(bad_zones)}")

        from google import genai
        client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location='global')
            
        response = await client.aio.models.generate_content(
            model='gemini-3.1-pro-preview',
            contents=prompt
        )
        text = response.text
        ai_elapsed = int((time.time() - ai_start) * 1000)
        response_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        print(f"[AI] Gemini response | elapsed={ai_elapsed}ms | response_hash={response_hash} | length={len(text)}")


        # ── Repetition Detection Guard ───────────────────────────────────────
        if not hasattr(get_policy_recommendations, "_response_hashes"):
            get_policy_recommendations._response_hashes = []
        recent = get_policy_recommendations._response_hashes
        if recent.count(response_hash) >= 3:
            print(f"[AI] ⚠ REPETITION DETECTED: response_hash={response_hash} appeared {recent.count(response_hash)}x in last {len(recent)} calls. AI may be unreliable.")
        recent.append(response_hash)
        if len(recent) > 10:
            recent.pop(0)

        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            recs_data = json.loads(match.group(0))
            return [Recommendation(**r) for r in recs_data[:3]]

        raise ValueError(f"AI response did not contain valid JSON array (hash={response_hash})")

    except Exception as e:
        print(f"[AI] Gemini FAILURE: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"AI policy engine failed: {str(e)}"
        )

# ─── Feature 4: Wind Grid (MeteoJSON format) ──────────────────────────────────

@router.get("/weather/wind-grid")
async def get_wind_grid():
    """
    Returns a 10x10 wind grid covering Delhi in MeteoJSON format (leaflet-velocity).
    """
    lat_num = 10
    lon_num = 10
    lat_max, lat_min = 28.9, 28.4
    lon_min, lon_max = 76.8, 77.4
    dlat = (lat_max - lat_min) / (lat_num - 1)
    dlon = (lon_max - lon_min) / (lon_num - 1)
    
    lats, lons = [], []
    for j in range(lat_num):
        lat = lat_max - (j * dlat)
        for i in range(lon_num):
            lon = lon_min + (i * dlon)
            lats.append(round(float(lat), 4))
            lons.append(round(float(lon), 4))
            
    url = f"https://api.open-meteo.com/v1/forecast?latitude={','.join(map(str, lats))}&longitude={','.join(map(str, lons))}&current=wind_speed_10m,wind_direction_10m"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=503, detail="Open-Meteo API failed to return wind data.")
        data = resp.json()
        
    if not isinstance(data, list):
        data = [data]

    import math
    u_vals, v_vals = [], []
    for item in data:
        current = item.get("current", {})
        spd = current.get("wind_speed_10m", 0)
        dir_deg = current.get("wind_direction_10m", 0)
        
        spd_ms = spd / 3.6
        rad = math.radians(dir_deg)
        u_vals.append(round(-spd_ms * math.sin(rad), 2))
        v_vals.append(round(-spd_ms * math.cos(rad), 2))
        
    return [
        {
            "header": {
                "parameterCategory": 2, "parameterNumber": 2, "parameterUnit": "m.s-1",
                "dx": dlon, "dy": dlat,
                "la1": lat_max, "la2": lat_min,
                "lo1": lon_min, "lo2": lon_max,
                "nx": lon_num, "ny": lat_num
            },
            "data": u_vals
        },
        {
            "header": {
                "parameterCategory": 2, "parameterNumber": 3, "parameterUnit": "m.s-1",
                "dx": dlon, "dy": dlat,
                "la1": lat_max, "la2": lat_min,
                "lo1": lon_min, "lo2": lon_max,
                "nx": lon_num, "ny": lat_num
            },
            "data": v_vals
        }
    ]

# [DEPRECATED: WAQI] — The /forecast endpoint used WAQI's forecast API
# (data.forecast.daily.pm25). OpenAQ does not provide forecast data — it only
# has historical/real-time measurements. This endpoint is removed.
# If forecast functionality is needed in the future, integrate Open-Meteo CAMS.
#
# class ForecastResponse(BaseModel):
#     time: str
#     pm25: float
#
# @router.get("/forecast", response_model=List[ForecastResponse])
# async def get_cams_forecast(lat: float, lon: float):
#     """
#     [DEPRECATED] Returns up to 8 days of PM2.5 ensemble forecast for a specific
#     coordinate using the WAQI API.
#     """
#     if not WAQI_TOKEN:
#         raise HTTPException(status_code=503, detail="WAQI_TOKEN is missing.")
#
#     url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={WAQI_TOKEN}"
#     async with httpx.AsyncClient(timeout=15.0) as client:
#         resp = await client.get(url)
#         if resp.status_code != 200:
#             raise HTTPException(status_code=503, detail="WAQI Forecast API failed.")
#         data = resp.json()
#
#     if data.get("status") != "ok":
#         raise HTTPException(status_code=503, detail="WAQI did not return valid forecast.")
#
#     daily_pm25 = data.get("data", {}).get("forecast", {}).get("daily", {}).get("pm25", [])
#
#     result = []
#     for item in daily_pm25:
#         result.append(ForecastResponse(
#             time=item["day"],
#             pm25=float(item.get("avg", item.get("max", 0.0)))
#         ))
#
#     return result
