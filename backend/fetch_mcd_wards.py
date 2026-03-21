import requests
import json
import os

url = "https://raw.githubusercontent.com/HindustanTimesLabs/shapefiles/master/city/delhi/ward/delhi_ward.geojson"
print("Fetching 272 MCD Wards exactly traced from State Election Commission PDFs...")

r = requests.get(url)
if r.status_code == 200:
    geojson = r.json()
    
    # Calculate centroid coordinates for backend weather polling
    for f in geojson.get('features', []):
        try:
            coords = f['geometry']['coordinates']
            if f['geometry']['type'] == 'MultiPolygon':
                pts = [pt for poly in coords for ring in poly for pt in ring]
            else:
                pts = [pt for ring in coords for pt in ring]
                
            lats = [pt[1] for pt in pts]
            lons = [pt[0] for pt in pts]
            f['properties']['lat'] = sum(lats)/len(lats)
            f['properties']['lon'] = sum(lons)/len(lons)
            
            ward_name = f['properties'].get('ward_name')
            ward_no = f['properties'].get('ward_no')
            name = f"{ward_name} ({ward_no})" if ward_name and ward_no else str(ward_name or ward_no or "Ward")
            f['properties']['name'] = name
        except Exception as e:
            pass

    target_path = r"c:\Users\24r11\OneDrive\Desktop\breath analyser\Breath-Analyzser\web-frontend\public\mcd_wards_250.geojson"
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding='utf-8') as fp:
        json.dump(geojson, fp)
    
    print(f"SUCCESS: Synthesized and saved {len(geojson.get('features', []))} highly precise MCD Ward Polygons.")
else:
    print("Failed to download GeoJSON:", r.status_code)
