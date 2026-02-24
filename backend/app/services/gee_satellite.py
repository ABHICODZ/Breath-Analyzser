import ee
import datetime
import logging
import pandas as pd
from typing import List, Dict

logger = logging.getLogger(__name__)

class EarthEngineSatellitePipeline:
    """
    Connects to Google Earth Engine to download Sentinel-5P TROPOMI Level-2 data.
    This provides satellite radiance data for Nitrogen Dioxide (NO2), Carbon Monoxide (CO), etc.
    """
    def __init__(self, service_account_json_path: str = None):
        """
        To run this, you must have a Google Cloud Project with the Earth Engine API enabled,
        and a Service Account JSON key.
        """
        self.is_initialized = False
        try:
            if service_account_json_path:
                from google.oauth2 import service_account
                scopes = ['https://www.googleapis.com/auth/earthengine']
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_json_path, scopes=scopes)
                ee.Initialize(credentials)
            else:
                # Triggers a browser authentication flow if no service account is provided
                ee.Authenticate()
                ee.Initialize()
            
            self.is_initialized = True
            logger.info("✅ Google Earth Engine Initialized.")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Earth Engine: {e}")

    def fetch_no2_radiance(self, bounding_box: List[float], days_back: int = 7) -> pd.DataFrame:
        """
        Fetches Sentinel-5P NO2 column number density for a specific area over the last N days.
        bounding_box: [min_lon, min_lat, max_lon, max_lat]
        """
        if not self.is_initialized:
            raise RuntimeError("Earth Engine not initialized. Please provide valid credentials.")

        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days_back)
        
        logger.info(f"Fetching Satellite NO2 data from {start_date.date()} to {end_date.date()}...")

        # Define the geographic region of interest
        region = ee.Geometry.Rectangle(bounding_box)

        # Access the Sentinel-5P NO2 dataset
        collection = (ee.ImageCollection('COPERNICUS/S5P/NRTI/L3_NO2')
                      .select('NO2_column_number_density')
                      .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                      .filterBounds(region))

        # In a full production app, you would reduce this vast image collection into a spatial grid,
        # run PCA (Principal Component Analysis) to reduce dimensionality, and return it.
        # This is the simplified data extraction call:
        
        try:
            # We take the mean across time for this example
            mean_image = collection.mean()
            
            # Sample rectangles in the region
            # (Note: getInfo() physically pulls the data from Google's servers to your local machine)
            sampled_data = mean_image.sampleRegions(
                collection=ee.FeatureCollection([ee.Feature(region)]),
                scale=1113.2,  # ~1km resolution for Sentinel-5p
                geometries=True
            ).getInfo()

            return self._process_gee_response(sampled_data)
            
        except Exception as e:
            logger.error(f"Failed to fetch satellite data: {e}")
            return pd.DataFrame()

    def _process_gee_response(self, gee_data: dict) -> pd.DataFrame:
        # Converts the messy Google Earth Engine JSON into a clean Pandas DataFrame
        if not gee_data or 'features' not in gee_data:
            return pd.DataFrame()
            
        rows = []
        for feature in gee_data['features']:
            props = feature.get('properties', {})
            geom = feature.get('geometry', {}).get('coordinates', [0, 0])
            rows.append({
                "lon": geom[0],
                "lat": geom[1],
                "no2_density": props.get('NO2_column_number_density', 0.0)
            })
            
        return pd.DataFrame(rows)

if __name__ == "__main__":
    import os
    # Dynamically find the path to the credentials file relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cred_path = os.path.join(script_dir, "ee-credentials.json")
    
    pipeline = EarthEngineSatellitePipeline(service_account_json_path=cred_path)
    # Bounding box for New Delhi, India: [76.84, 28.40, 77.34, 28.88]
    df = pipeline.fetch_no2_radiance(bounding_box=[76.84, 28.40, 77.34, 28.88], days_back=1)
    print(df.head())
