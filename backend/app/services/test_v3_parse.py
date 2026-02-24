import requests
import json

url = "https://api.openaq.org/v3/locations"
h = {"X-API-Key": "a48c3556e253887d4098147a13ff033b81ccd7ac36fede20ff5c3b8eb7be4029"}
# Query 50 km around Delhi
params = {"coordinates": "28.6139,77.2090", "radius": 25000, "limit": 5}
r = requests.get(url, headers=h, params=params)

data = r.json()
print("Keys in response:", data.keys())
if 'results' in data:
    for loc in data['results']:
        name = loc.get('name')
        coords = loc.get('coordinates', {})
        print(f"Location: {name}, lat: {coords.get('latitude')}, lon: {coords.get('longitude')}")
        sensors = loc.get('sensors', [])
        for s in sensors:
            param = s.get('parameter', {}).get('name')
            latest = s.get('latest', {})
            val = latest.get('value') if latest else None
            print(f"  - {param}: {val}")
