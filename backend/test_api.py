#!/usr/bin/env python3
"""
Basic API Endpoint Tests
Tests all main API endpoints to ensure they respond correctly.
Run: .venv/bin/python backend/test_api.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8002"

def test_endpoint(method, endpoint, data=None, expected_status=200):
    """Test a single API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=5)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=5)
        else:
            print(f"❌ Unknown method: {method}")
            return False
        
        if response.status_code == expected_status:
            print(f"✅ {method} {endpoint} - Status {response.status_code}")
            return True
        else:
            print(f"❌ {method} {endpoint} - Expected {expected_status}, got {response.status_code}")
            print(f"   Response: {response.text[:100]}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {method} {endpoint} - Connection error: {e}")
        return False

def main():
    print("=" * 60)
    print("Energy AI Management System - API Tests")
    print("=" * 60)
    print()
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Root endpoint
    tests_total += 1
    if test_endpoint("GET", "/"):
        tests_passed += 1
    
    # Test 2: Get rooms status
    tests_total += 1
    if test_endpoint("GET", "/api/rooms"):
        tests_passed += 1
    
    # Test 3: Webcam test status
    tests_total += 1
    if test_endpoint("GET", "/api/webcam/test/status"):
        tests_passed += 1
    
    # Test 4: Update occupancy
    tests_total += 1
    if test_endpoint("POST", "/api/occupancy", 
                     data={"room_id": "Classroom", "occupied": True}):
        tests_passed += 1
    
    # Test 5: CCTV status (should work even without connection)
    tests_total += 1
    if test_endpoint("GET", "/api/cctv/status/Classroom"):
        tests_passed += 1
    
    # Test 6: Reset occupancy
    tests_total += 1
    if test_endpoint("POST", "/api/occupancy", 
                     data={"room_id": "Classroom", "occupied": False}):
        tests_passed += 1
    
    # Test 7: Invalid room (should fail with 404)
    tests_total += 1
    if test_endpoint("POST", "/api/occupancy", 
                     data={"room_id": "InvalidRoom", "occupied": True},
                     expected_status=404):
        tests_passed += 1
    
    print()
    print("=" * 60)
    print(f"Test Results: {tests_passed}/{tests_total} passed")
    print("=" * 60)
    
    if tests_passed == tests_total:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {tests_total - tests_passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
