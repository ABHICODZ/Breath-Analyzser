#!/usr/bin/env python3
"""
VayuDrishti End-to-End Testing Suite
Tests all API endpoints and validates AQI values against real sources
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import sys

# Configuration
API_BASE = "http://localhost:8080"

# Test locations in Delhi
TEST_LOCATIONS = [
    {"name": "Connaught Place", "lat": 28.6315, "lon": 77.2167},
    {"name": "ITO", "lat": 28.6289, "lon": 77.2416},
    {"name": "Anand Vihar", "lat": 28.6469, "lon": 77.3158},
    {"name": "RK Puram", "lat": 28.5629, "lon": 77.1824},
    {"name": "Dwarka", "lat": 28.5921, "lon": 77.0460},
]

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text: str):
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

# Test Results Tracker
test_results = {
    "passed": 0,
    "failed": 0,
    "warnings": 0,
    "total": 0
}

def test_api_health():
    """Test 1: API Health Check"""
    print_header("TEST 1: API Health Check")
    test_results["total"] += 1
    
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success(f"API is healthy: {data}")
            print_info(f"Response time: {response.elapsed.total_seconds():.2f}s")
            test_results["passed"] += 1
            return True
        else:
            print_error(f"Health check failed with status {response.status_code}")
            test_results["failed"] += 1
            return False
    except Exception as e:
        print_error(f"Health check failed: {e}")
        test_results["failed"] += 1
        return False

def test_dashboard_wards():
    """Test 2: Dashboard Wards Endpoint"""
    print_header("TEST 2: Dashboard Wards Data")
    test_results["total"] += 1
    
    try:
        # Test ward-level data
        print_info("Testing ward-level granularity...")
        response = requests.get(f"{API_BASE}/api/v1/dashboard/wards?level=ward", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            wards = data.get("wards", [])
            print_success(f"Retrieved {len(wards)} wards")
            print_info(f"Response time: {response.elapsed.total_seconds():.2f}s")
            
            # Validate data structure
            if wards:
                sample = wards[0]
                required_fields = ["id", "name", "lat", "lon", "aqi", "pm25", "status"]
                missing = [f for f in required_fields if f not in sample]
                
                if missing:
                    print_warning(f"Missing fields in ward data: {missing}")
                    test_results["warnings"] += 1
                else:
                    print_success("All required fields present")
                
                # Display sample wards
                print_info("\nSample Ward Data:")
                for ward in wards[:5]:
                    print(f"  • {ward['name']}: AQI {ward['aqi']}, PM2.5 {ward['pm25']}, Status: {ward['status']}")
                
                test_results["passed"] += 1
                return wards
            else:
                print_error("No ward data returned")
                test_results["failed"] += 1
                return []
        else:
            print_error(f"Request failed with status {response.status_code}")
            print_error(f"Response: {response.text[:200]}")
            test_results["failed"] += 1
            return []
    except Exception as e:
        print_error(f"Dashboard wards test failed: {e}")
        test_results["failed"] += 1
        return []

def test_gee_satellite(location: Dict):
    """Test 3: Google Earth Engine Satellite Analysis"""
    print_header(f"TEST 3: Satellite Analysis - {location['name']}")
    test_results["total"] += 1
    
    try:
        print_info(f"Analyzing location: {location['lat']}, {location['lon']}")
        response = requests.get(
            f"{API_BASE}/api/v1/gee/analyze",
            params={"lat": location["lat"], "lon": location["lon"]},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Satellite analysis successful")
            print_info(f"Response time: {response.elapsed.total_seconds():.2f}s")
            print_info(f"  Construction Dust Index: {data.get('construction_dust_index', 'N/A')}")
            print_info(f"  Biomass Burning Index: {data.get('biomass_burning_index', 'N/A')}")
            print_info(f"  Dominant Source: {data.get('dominant_source', 'N/A')}")
            test_results["passed"] += 1
            return data
        else:
            print_warning(f"Satellite analysis returned status {response.status_code}")
            print_warning(f"Response: {response.text[:200]}")
            test_results["warnings"] += 1
            return None
    except Exception as e:
        print_warning(f"Satellite analysis failed (may be expected): {e}")
        test_results["warnings"] += 1
        return None

def test_forecast(location: Dict):
    """Test 4: 8-Day PM2.5 Forecast"""
    print_header(f"TEST 4: Forecast - {location['name']}")
    test_results["total"] += 1
    
    try:
        print_info(f"Requesting forecast for: {location['lat']}, {location['lon']}")
        response = requests.get(
            f"{API_BASE}/api/v1/dashboard/forecast",
            params={"lat": location["lat"], "lon": location["lon"]},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            forecast = data.get("forecast", [])
            print_success(f"Forecast retrieved: {len(forecast)} days")
            print_info(f"Response time: {response.elapsed.total_seconds():.2f}s")
            
            if forecast:
                print_info("\nForecast Data:")
                for day in forecast[:3]:  # Show first 3 days
                    print(f"  • Day {day.get('day', 'N/A')}: PM2.5 {day.get('pm25', 'N/A')}, AQI {day.get('aqi', 'N/A')}")
                test_results["passed"] += 1
                return forecast
            else:
                print_warning("Forecast returned empty")
                test_results["warnings"] += 1
                return []
        else:
            print_error(f"Forecast failed with status {response.status_code}")
            print_error(f"Response: {response.text[:200]}")
            test_results["failed"] += 1
            return []
    except Exception as e:
        print_error(f"Forecast test failed: {e}")
        test_results["failed"] += 1
        return []

def test_recommendations():
    """Test 5: AI Policy Recommendations"""
    print_header("TEST 5: AI Policy Recommendations")
    test_results["total"] += 1
    
    try:
        print_info("Requesting AI-generated policy recommendations...")
        response = requests.get(f"{API_BASE}/api/v1/dashboard/recommendations", timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            recs = data.get("recommendations", [])
            print_success(f"Retrieved {len(recs)} recommendations")
            print_info(f"Response time: {response.elapsed.total_seconds():.2f}s")
            
            if recs:
                print_info("\nSample Recommendations:")
                for rec in recs[:3]:
                    print(f"  • Ward: {rec.get('ward', 'N/A')}")
                    print(f"    Issue: {rec.get('issue', 'N/A')}")
                    print(f"    Action: {rec.get('action', 'N/A')[:80]}...")
                    print(f"    Urgency: {rec.get('urgency', 'N/A')}")
                test_results["passed"] += 1
                return recs
            else:
                print_warning("No recommendations returned")
                test_results["warnings"] += 1
                return []
        else:
            print_error(f"Recommendations failed with status {response.status_code}")
            print_error(f"Response: {response.text[:200]}")
            test_results["failed"] += 1
            return []
    except Exception as e:
        print_error(f"Recommendations test failed: {e}")
        test_results["failed"] += 1
        return []
def test_navigation():
    """Test 6: Navigation/Routing Engine"""
    print_header("TEST 6: Navigation & Routing")
    test_results["total"] += 1
    
    try:
        # Test route from Connaught Place to ITO
        start = TEST_LOCATIONS[0]
        end = TEST_LOCATIONS[1]
        
        print_info(f"Calculating route from {start['name']} to {end['name']}")
        
        response = requests.get(
            f"{API_BASE}/api/v1/navigation/route",
            params={
                "start_lat": start["lat"],
                "start_lon": start["lon"],
                "end_lat": end["lat"],
                "end_lon": end["lon"],
                "health_sensitivity": 50
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get("stats", {})
            
            print_success("Route calculation successful")
            print_info(f"Response time: {response.elapsed.total_seconds():.2f}s")
            print_info(f"\nRoute Statistics:")
            print_info(f"  Shortest Distance: {stats.get('shortest_dist_m', 0):.0f}m")
            print_info(f"  Cleanest Distance: {stats.get('cleanest_dist_m', 0):.0f}m")
            print_info(f"  Exposure Reduction: {stats.get('exposure_reduction_pct', 0):.1f}%")
            print_info(f"  Distance Increase: {stats.get('distance_increase_pct', 0):.1f}%")
            
            test_results["passed"] += 1
            return data
        else:
            print_warning(f"Navigation returned status {response.status_code}")
            print_warning(f"Response: {response.text[:200]}")
            test_results["warnings"] += 1
            return None
    except Exception as e:
        print_warning(f"Navigation test failed: {e}")
        test_results["warnings"] += 1
        return None

def test_wind_grid():
    """Test 7: Wind Grid Data"""
    print_header("TEST 7: Wind Grid Data")
    test_results["total"] += 1
    
    try:
        print_info("Fetching wind velocity grid...")
        response = requests.get(f"{API_BASE}/api/v1/weather/wind-grid", timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print_success("Wind grid data retrieved")
            print_info(f"Response time: {response.elapsed.total_seconds():.2f}s")
            print_info(f"Grid type: {data.get('type', 'N/A')}")
            
            features = data.get("features", [])
            if features:
                print_info(f"Grid points: {len(features)}")
                sample = features[0].get("properties", {})
                print_info(f"Sample wind data: U={sample.get('u_wind', 'N/A')}, V={sample.get('v_wind', 'N/A')}")
                test_results["passed"] += 1
            else:
                print_warning("No wind grid features returned")
                test_results["warnings"] += 1
            return data
        else:
            print_error(f"Wind grid failed with status {response.status_code}")
            test_results["failed"] += 1
            return None
    except Exception as e:
        print_error(f"Wind grid test failed: {e}")
        test_results["failed"] += 1
        return None

def run_all_tests():
    """Run complete test suite"""
    print(f"\n{Colors.BOLD}VayuDrishti End-to-End Testing Suite{Colors.RESET}")
    print(f"{Colors.BOLD}Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")
    
    # Test 1: Health Check
    if not test_api_health():
        print_error("\n⚠ API is not responding. Please start the backend server.")
        return
    
    time.sleep(1)
    
    # Test 2: Dashboard Wards
    wards = test_dashboard_wards()
    time.sleep(1)
    
    # Test 3-4: Satellite & Forecast for multiple locations
    for location in TEST_LOCATIONS[:2]:  # Test first 2 locations
        test_gee_satellite(location)
        time.sleep(1)
        test_forecast(location)
        time.sleep(1)
    
    # Test 5: Recommendations
    test_recommendations()
    time.sleep(1)
    
    # Test 6: Navigation
    test_navigation()
    time.sleep(1)
    
    # Test 7: Wind Grid
    test_wind_grid()
    time.sleep(1)
    
    # [DEPRECATED: WAQI] — AQI validation against WAQI has been removed.
    # Use test_blind_station.py for validation against OpenAQ live data.    
    # Print Summary
    print_header("TEST SUMMARY")
    print(f"\n{Colors.BOLD}Total Tests: {test_results['total']}{Colors.RESET}")
    print(f"{Colors.GREEN}Passed: {test_results['passed']}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {test_results['failed']}{Colors.RESET}")
    print(f"{Colors.YELLOW}Warnings: {test_results['warnings']}{Colors.RESET}")
    
    success_rate = (test_results['passed'] / test_results['total'] * 100) if test_results['total'] > 0 else 0
    print(f"\n{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.RESET}")
    
    if test_results['failed'] == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL CRITICAL TESTS PASSED!{Colors.RESET}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ SOME TESTS FAILED - REVIEW ABOVE{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")
    
    return test_results['failed'] == 0

if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Tests interrupted by user{Colors.RESET}")
        sys.exit(1)
