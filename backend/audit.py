import time
import requests
import json
import sys

endpoints = [
    'http://localhost:8080/api/v1/dashboard/wards?level=district',
    'http://localhost:8080/api/v1/dashboard/wards?level=ward',
    'http://localhost:8080/api/v1/dashboard/recommendations',
    'http://localhost:8080/api/v1/gee/analyze?lat=28.6139&lon=77.2090'
]

print("--- API ZERO-HALLUCINATION AUDIT ---")
for url in endpoints:
    start = time.time()
    name = url.split('/')[-1]
    try:
        r = requests.get(url, timeout=5)
        elapsed = int((time.time() - start) * 1000)
        
        if r.status_code == 200:
            data = r.json()
            items = len(data) if isinstance(data, list) else 1
            print(f"PASS | {elapsed:4d}ms | {name} | Items: {items}")
        else:
            try:
                err = str(r.json())[:100]
            except:
                err = r.text[:100]
            print(f"FAIL | {elapsed:4d}ms | {name} | HTTP {r.status_code} | Err: {err}")
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        print(f"FAIL | {elapsed:4d}ms | {name} | Exception: {str(e)[:150]}")
    sys.stdout.flush()
