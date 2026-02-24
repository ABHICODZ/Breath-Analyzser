import requests
import datetime
import pandas as pd
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class CPCBSensorAPI:
    """
    Connects to the Central Pollution Control Board (CPCB) of India 
    or OpenAQ to fetch live ground-level air quality data.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://api.openaq.org/v3"
        self.headers = {"X-API-Key": self.api_key} if self.api_key else {}
    def fetch_live_city_data(self, lat: float = 28.6139, lon: float = 77.2090, radius_meters: int = 25000) -> pd.DataFrame:
        """
        Fetches the latest PM2.5, PM10, and NO2 readings for all government 
        sensor stations within a bounding radius.
        """
        logger.info(f"Fetching live government sensor locations around {lat},{lon}...")
        
        endpoint = f"{self.base_url}/locations"
        params = {
            "coordinates": f"{lat},{lon}",
            "radius": radius_meters,
            "limit": 100
        }

        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get('results', [])
            logger.info(f"OpenAQ returned {len(results)} raw location results.")
            
            clean_data = []
            for loc in results:
                loc_id = loc.get('id')
                station_name = loc.get('name')
                coords = loc.get('coordinates', {})
                latitude = coords.get('latitude')
                longitude = coords.get('longitude')
                
                if not loc_id: continue
                
                endpoint_data = f"{self.base_url}/locations/{loc_id}/latest"
                res_data = requests.get(endpoint_data, headers=self.headers)
                
                if res_data.status_code == 200:
                    latest_data = res_data.json().get('results', [])
                    
                    record = {
                        "station_name": station_name,
                        "lat": latitude,
                        "lon": longitude,
                        "time": datetime.datetime.now(datetime.timezone.utc)
                    }
                    
                    sensors_meta = loc.get('sensors', [])
                    sensor_map = {
                        s.get('id'): s.get('parameter', {}).get('name') 
                        for s in sensors_meta if s.get('id')
                    }
                    
                    for reading in latest_data:
                        sensor_id = reading.get('sensorsId')
                        val = reading.get('value')
                        param = sensor_map.get(sensor_id)
                        
                        if val is not None and param is not None:
                            if param == 'pm2.5' or param == 'pm25': record['pm2_5'] = val
                            elif param == 'pm10': record['pm10'] = val
                            elif param == 'no2': record['no2'] = val
                    
                    if 'pm2_5' in record or 'pm10' in record or 'no2' in record:
                        clean_data.append(record)
                        
            return pd.DataFrame(clean_data)
            
            
        except requests.exceptions.HTTPError as e:
             if response.status_code == 401:
                 logger.error("❌ API Key invalid or missing.")
             elif response.status_code == 429:
                 logger.error("❌ Rate limit exceeded.")
             elif response.status_code == 422:
                 logger.error(f"❌ HTTP 422 Error. Validation error from server: {response.text}")
             else:
                 logger.error(f"❌ HTTP Error: {e}")
             return pd.DataFrame()
        except Exception as e:
            logger.error(f"❌ Failed to fetch sensor data: {e}")
            return pd.DataFrame()


if __name__ == "__main__":
    # Test script: You can get a free API key at https://openaq.org/developers/
    api = CPCBSensorAPI(api_key="a48c3556e253887d4098147a13ff033b81ccd7ac36fede20ff5c3b8eb7be4029")
    # Fetching for default test coordinates (Delhi)
    df = api.fetch_live_city_data()
    print(f"Fetched data from {len(df)} stations.")
    if not df.empty:
        print(df.head())
