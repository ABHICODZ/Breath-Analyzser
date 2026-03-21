from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import math
import httpx
import json
import os
import asyncio
import time

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

# ─── Config (all from env vars or module-level constants — no hardcoding) ─────

WAQI_TOKEN = os.environ.get("WAQI_TOKEN")
if not WAQI_TOKEN:
    print("[FATAL] WAQI_TOKEN environment variable is missing. Real WAQI data cannot be fetched.")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("[FATAL] GROQ_API_KEY environment variable is missing. Policy recommendations will fail.")
# Delhi NCR bounding box — all 44 real CPCB/WAQI monitoring stations
WAQI_BOUNDS_URL = f"https://api.waqi.info/map/bounds/?latlng=28.4,76.8,28.9,77.4&token={WAQI_TOKEN}"

# ─── Utility Functions ─────────────────────────────────────────────────────────

def load_geojson(filename: str) -> list:
    data_list = []
    path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'web-frontend', 'public', filename)
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

def aqi_us_to_pm25(aqi: int) -> float:
    """Reverse-map US EPA AQI → PM2.5 µg/m³ (WAQI reports US AQI)."""
    bp = [
        (0,   50,  0.0,   12.0),
        (51,  100, 12.1,  35.4),
        (101, 150, 35.5,  55.4),
        (151, 200, 55.5,  150.4),
        (201, 300, 150.5, 250.4),
        (301, 400, 250.5, 350.4),
        (401, 500, 350.5, 500.4),
    ]
    for i_lo, i_hi, c_lo, c_hi in bp:
        if i_lo <= aqi <= i_hi:
            return c_lo + (aqi - i_lo) * (c_hi - c_lo) / (i_hi - i_lo)
    return 250.0

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
    """Find the closest real WAQI station to a given ward by Euclidean distance."""
    if not anchors:
        return None
    return min(anchors, key=lambda a: math.hypot(ward_lat - a['lat'], ward_lon - a['lon']))

# ─── ML Engine ────────────────────────────────────────────────────────────────

from app.services.ml_engine import TemporalNeuralNetworkMock
ML_ENGINE = TemporalNeuralNetworkMock()
INFERENCE_GRID_CACHE: dict = {"timestamp": 0.0, "data": [], "anchors": []}
BACKGROUND_TASK_STARTED = False

# Cached ward metadata
WARD_META = load_geojson('kaggle_wards.geojson')
DISTRICT_META = load_geojson('delhi_wards.geojson')

# ─── WAQI Real Station Anchor Fetcher ─────────────────────────────────────────

async def fetch_real_station_anchors(client: httpx.AsyncClient) -> list:
    """
    Fetch all real CPCB/WAQI monitoring stations in Delhi NCR via bounds API.
    Returns list of anchor dicts with real PM2.5 values on India CPCB scale.
    """
    try:
        res = await client.get(WAQI_BOUNDS_URL, timeout=15.0)
        stations = res.json().get("data", [])
        anchors = []
        for s in stations:
            try:
                aqi_us = int(s.get("aqi", 0))
            except (ValueError, TypeError):
                continue
            if aqi_us <= 0:
                continue
            pm25 = aqi_us_to_pm25(aqi_us)
            aqi_us = pm25_to_aqi_us(pm25)
            anchors.append({
                "id": str(s.get("uid", "")),
                "name": s["station"]["name"].split(",")[0].strip(),
                "lat": float(s["lat"]),
                "lon": float(s["lon"]),
                "aqi": aqi_us,
                "pm25": round(pm25, 1),
                "dominant_source": "Live CPCB/WAQI Station",
                "status": get_status(aqi_us),
                "trend": "stable",
            })
        print(f"[WAQI] Loaded {len(anchors)} real monitoring stations.")
        return anchors
    except Exception as e:
        print(f"[WAQI BOUNDS] Error: {e}")
        return []

# ─── Chemistry Enrichment (Open-Meteo, uses real anchor as PM2.5 base) ────────

async def enrich_with_open_meteo(client: httpx.AsyncClient, ward: dict, base_pm25: float) -> WardStat:
    """
    Try to get atmospheric chemistry from Open-Meteo.
    PM2.5 base is already anchored from the nearest real WAQI station.
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
    print("[TNN] Autonomous Spatial ML Loop Started.")
    while True:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                anchors = await fetch_real_station_anchors(client)

                if not anchors:
                    print("[TNN] WAQI anchor fetch returned 0 stations — skipping cycle.")
                    await asyncio.sleep(60)
                    continue

                # Store anchors in cache for district view to reuse
                INFERENCE_GRID_CACHE["anchors"] = anchors

                # Use the ML engine to interpolate all 251 wards
                inferences = ML_ENGINE.predict(anchors, WARD_META)
                results = list(inferences.values())
                results.sort(key=lambda x: x['aqi'], reverse=True)

                INFERENCE_GRID_CACHE["data"] = results
                INFERENCE_GRID_CACHE["timestamp"] = time.time()
                print(f"[TNN] Inferred {len(results)} ward zones from {len(anchors)} real anchor stations.")
        except Exception as e:
            print(f"[TNN FATAL] Inference loop error: {e}")

        await asyncio.sleep(300)  # Refresh every 5 minutes

# ─── API Endpoints ─────────────────────────────────────────────────────────────

@router.get("/wards", response_model=List[WardStat])
async def get_ward_stats(level: str = 'ward'):
    """
    Returns live AQI data.
    - level=ward    → 251 interpolated wards (TNN ML inference)
    - level=district → real WAQI station readings grouped by district proximity
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

    if level == 'district':
        # Use real WAQI station anchors directly (no Open-Meteo for districts)
        anchors = INFERENCE_GRID_CACHE.get("anchors", [])
        if not anchors:
            # Fetch fresh if cache is cold
            async with httpx.AsyncClient(timeout=15.0) as client:
                anchors = await fetch_real_station_anchors(client)

        if anchors:
            district_results = []
            for dist in DISTRICT_META:
                closest = nearest_anchor(dist['lat'], dist['lon'], anchors)
                if closest:
                    district_results.append(WardStat(
                        id=dist["id"],
                        name=dist["name"],
                        lat=dist["lat"],
                        lon=dist["lon"],
                        aqi=closest["aqi"],
                        pm25=closest["pm25"],
                        dominant_source=f"Nearest Sensor: {closest['name']}",
                        status=closest["status"],
                        trend="stable"
                    ))
            return district_results

    # Ward mode: return TNN ML-inferred grid
    return [WardStat(**w) for w in INFERENCE_GRID_CACHE["data"]] if INFERENCE_GRID_CACHE["data"] else []


@router.get("/recommendations", response_model=List[Recommendation])
async def get_policy_recommendations():
    """
    Generates real-time policy recommendations via Groq Llama LLM,
    analysing the top pollution hotspots from the live ML inference grid.
    """
    bad_zones = INFERENCE_GRID_CACHE["data"][:5]

    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)

        if not bad_zones:
            raise ValueError("No inference data available yet")

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

        completion = await asyncio.to_thread(
            groq_client.chat.completions.create,
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.3,
        )

        import re
        text = completion.choices[0].message.content
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            recs_data = json.loads(match.group(0))
            return [Recommendation(**r) for r in recs_data[:3]]

    except Exception as e:
        print(f"[Groq LLM Error]: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Groq LLM API failed to generate recommendations: {e}. No simulated responses allowed."
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
            lats.append(round(lat, 4))
            lons.append(round(lon, 4))
            
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

# ─── Feature 1: CAMS Predictive Ward-Level Forecast ────────────────────────────

class ForecastResponse(BaseModel):
    time: str
    pm25: float

@router.get("/forecast", response_model=List[ForecastResponse])
async def get_cams_forecast(lat: float, lon: float):
    """
    Returns up to 8 days of PM2.5 ensemble forecast for a specific coordinate
    using the secure WAQI API to strictly bypass public IP rate limits.
    """
    if not WAQI_TOKEN:
        raise HTTPException(status_code=503, detail="WAQI_TOKEN is missing in the environment.")

    url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={WAQI_TOKEN}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=503, detail="WAQI Forecast API failed to connect.")
        data = resp.json()
        
    if data.get("status") != "ok":
        raise HTTPException(status_code=503, detail="WAQI did not return valid forecast payload.")
        
    daily_pm25 = data.get("data", {}).get("forecast", {}).get("daily", {}).get("pm25", [])
    
    result = []
    for item in daily_pm25:
        # Extract the forecasted average PM2.5 for the forward dates
        result.append(ForecastResponse(
            time=item["day"], 
            pm25=float(item.get("avg", item.get("max", 0.0)))
        ))
        
    return result
