import asyncio
from app.services.openaq_client import openaq_client
from app.core.stations import STATION_COORDS
import logging

logging.basicConfig(level=logging.INFO)

def main():
    print("Building MLOps Feature Matrix...")
    matrix, temp_hum = openaq_client.build_feature_matrix(STATION_COORDS)
    
    print("\n--- MATRIX SHAPE ---")
    print(matrix.shape)
    
    print("\n--- FIRST 5 ROWS ---")
    print(matrix[:5])
    
    print("\n--- TEMP/HUM DICT (first 5) ---")
    for k in range(5):
        print(f"Index {k}: {temp_hum[k]}")

if __name__ == "__main__":
    main()
