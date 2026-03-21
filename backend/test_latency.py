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

print('--- API LATENCY & STATUS TEST ---')
results = []
for url in endpoints:
    start = time.time()
    try:
        r = requests.get(url, timeout=45)
        elapsed = time.time() - start
        
        status = r.status_code
        data = r.json()
        item_count = len(data) if isinstance(data, list) else 1
        
        if status == 200:
            res = f'[{status}] {elapsed:5.2f}s | {url.split("/")[-1]} | items: {item_count}'
        else:
            res = f'[{status}] {elapsed:5.2f}s | {url.split("/")[-1]} | error: {data}'
    except Exception as e:
        elapsed = time.time() - start
        res = f'[FAIL] {elapsed:5.2f}s | {url} | {e}'
        
    print(res)
    sys.stdout.flush()
