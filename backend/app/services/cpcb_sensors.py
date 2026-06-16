"""
===========================================================================
 VAYU DRISHTI — CPCB Sensor Data Service
===========================================================================
 [DEPRECATED: WAQI] — This module previously used a mix of OpenAQ v2/v3.
 As of 2026-06-15, all live data fetching has been centralized in:
   → app/services/openaq_client.py (OpenAQClient)

 This file is kept for backward compatibility. The CPCBSensorAPI class
 below wraps the new OpenAQClient to maintain the same interface.
===========================================================================
"""

import logging
import pandas as pd
from typing import Dict

from app.core.stations import STATION_COORDS
from app.services.openaq_client import openaq_client, OpenAQRateLimitError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class CPCBSensorAPI:
    """
    Fetches live government sensor data from OpenAQ v3.
    
    This is a compatibility wrapper around the centralized OpenAQClient.
    For new code, use openaq_client directly from app.services.openaq_client.
    """

    def __init__(self, api_key: str = None):
        # The OpenAQ client uses OPENAQ_API_KEY env var or the hardcoded default
        self.client = openaq_client

    def fetch_live_city_data(
        self, lat: float = 28.6139, lon: float = 77.2090, radius_meters: int = 25000
    ) -> pd.DataFrame:
        """
        Fetches the latest PM2.5, PM10, NO2, SO2, CO readings for all 40
        CPCB stations defined in STATION_COORDS.

        Returns a DataFrame with columns:
          station_name, lat, lon, pm2_5, pm10, no2, so2, co, timestamp

        STRICT DATA INTEGRITY:
          - Only returns stations with real live data from OpenAQ.
          - NEVER injects fabricated/default/estimated values.
          - If rate limited, raises OpenAQRateLimitError.
          - If no data available, returns an empty DataFrame.
        """
        logger.info(f"[CPCBSensorAPI] Fetching live data for {len(STATION_COORDS)} stations...")

        try:
            readings, failed, error_msg = self.client.fetch_all_latest(STATION_COORDS)
        except OpenAQRateLimitError:
            logger.error(
                "[CPCBSensorAPI] OpenAQ API rate limit reached. "
                "Live data is temporarily unavailable."
            )
            raise

        if not readings:
            logger.error("[CPCBSensorAPI] No valid readings returned from OpenAQ.")
            return pd.DataFrame()

        records = []
        for r in readings:
            records.append({
                "station_name": r.name,
                "lat": r.lat,
                "lon": r.lon,
                "pm2_5": r.pm25,
                "pm10": r.pm10,
                "no2": r.no2,
                "so2": r.so2,
                "co": r.co,
                "timestamp": r.timestamp,
            })

        df = pd.DataFrame(records)
        logger.info(
            f"[CPCBSensorAPI] Returned {len(df)} stations with live data "
            f"({len(failed)} had no data)."
        )
        return df


# ═══════════════════════════════════════════════════════════════════════════════
# [DEPRECATED: WAQI/OpenAQ-v2 Legacy Code]
# The original CPCBSensorAPI implementation is preserved below for reference.
# It used OpenAQ v2/v3 endpoints directly with per-location requests.
# This has been replaced by the centralized OpenAQClient which handles:
#   - Rate limiting with exponential backoff
#   - Strict no-fabrication policy
#   - Station ID caching
#   - Unit filtering (µg/m³ only)
#
# class CPCBSensorAPI_Legacy:
#     def __init__(self, api_key: str = None):
#         self.api_key = api_key
#         self.base_url = "https://api.openaq.org/v3"
#         self.headers = {"X-API-Key": self.api_key} if self.api_key else {}
#
#     def fetch_live_city_data(self, lat=28.6139, lon=77.2090, radius_meters=25000):
#         endpoint = f"{self.base_url}/locations"
#         params = {"coordinates": f"{lat},{lon}", "radius": radius_meters, "limit": 100}
#         response = requests.get(endpoint, headers=self.headers, params=params)
#         response.raise_for_status()
#         data = response.json()
#         results = data.get('results', [])
#         clean_data = []
#         for loc in results:
#             loc_id = loc.get('id')
#             ...
#         return pd.DataFrame(clean_data)
# ═══════════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    api = CPCBSensorAPI()
    df = api.fetch_live_city_data()
    print(f"Fetched data from {len(df)} stations.")
    if not df.empty:
        print(df.to_string(index=False))
