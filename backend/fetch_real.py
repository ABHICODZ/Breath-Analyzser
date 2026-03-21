import requests
import json
import time
import os

districts = [
    "Central Delhi", "East Delhi", "New Delhi", "North Delhi",
    "North East Delhi", "North West Delhi", "Shahdara", 
    "South Delhi", "South East Delhi", "South West Delhi", "West Delhi"
]

features = []
for d in districts:
    url = f"https://nominatim.openstreetmap.org/search.php?q={d.replace(' ', '+')},+Delhi,+India&polygon_geojson=1&format=jsonv2"
    headers = {'User-Agent': 'VayuDrishti-Hackathon-App/1.0'}
    
    try:
        res = requests.get(url, headers=headers).json()
        if len(res) > 0:
            place = res[0]
            if place.get('geojson', {}).get('type') in ['Polygon', 'MultiPolygon']:
                features.append({
                    "type": "Feature",
                    "properties": {
                        "name": d,
                        "lat": float(place['lat']),
                        "lon": float(place['lon'])
                    },
                    "geometry": place['geojson']
                })
                print(f"Downloaded boundary for {d}")
    except Exception as e:
        print(f"Error fetching {d}: {e}")

geojson = {
    "type": "FeatureCollection",
    "features": features
}

target_path = r"c:\Users\24r11\OneDrive\Desktop\breath analyser\Breath-Analyzser\web-frontend\public\delhi_wards.geojson"
os.makedirs(os.path.dirname(target_path), exist_ok=True)

with open(target_path, "w", encoding='utf-8') as f:
    json.dump(geojson, f)

print(f"\nSUCCESS: Generated GeoJSON with {len(features)} real Delhi districts!")
