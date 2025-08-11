#!/usr/bin/env python3
"""
Test script for counter endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_counter_endpoints():
    """Test all counter endpoints"""
    print("🧪 Testing Counter Endpoints")
    print("=" * 40)
    
    # Test 1: Increment default counter
    print("\n1️⃣ Testing counter increment (default):")
    try:
        response = requests.post(f"{BASE_URL}/api/counter/increment", 
                               json={}, 
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data['message']}")
            print(f"   Count: {data['counter']['count']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Increment named counter
    print("\n2️⃣ Testing counter increment (named 'test'):")
    try:
        response = requests.post(f"{BASE_URL}/api/counter/increment", 
                               json={"name": "test"}, 
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data['message']}")
            print(f"   Count: {data['counter']['count']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Increment multiple times
    print("\n3️⃣ Testing multiple increments:")
    for i in range(3):
        try:
            response = requests.post(f"{BASE_URL}/api/counter/increment", 
                                   json={"name": "rapid"}, 
                                   headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Increment {i+1}: Count = {data['counter']['count']}")
            else:
                print(f"❌ Failed increment {i+1}: {response.status_code}")
        except Exception as e:
            print(f"❌ Error on increment {i+1}: {e}")
        
        time.sleep(0.1)  # Small delay
    
    # Test 4: Get specific counter
    print("\n4️⃣ Testing get counter:")
    try:
        response = requests.get(f"{BASE_URL}/api/counter/test")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Counter 'test': {data['counter']['count']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: Get all counters
    print("\n5️⃣ Testing get all counters:")
    try:
        response = requests.get(f"{BASE_URL}/api/counters")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} counters:")
            for counter in data['counters']:
                print(f"   - {counter['name']}: {counter['count']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 6: Test non-existent counter
    print("\n6️⃣ Testing non-existent counter:")
    try:
        response = requests.get(f"{BASE_URL}/api/counter/nonexistent")
        
        if response.status_code == 404:
            print("✅ Correctly returned 404 for non-existent counter")
        else:
            print(f"❌ Expected 404, got {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🎉 Counter endpoint tests completed!")

def simple_increment_test():
    """Simple test that just increments a counter"""
    print("🔥 Simple Counter Increment Test")
    print("=" * 35)
    
    try:
        response = requests.post(f"{BASE_URL}/api/counter/increment")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Counter incremented!")
            print(f"   Name: {data['counter']['name']}")
            print(f"   Count: {data['counter']['count']}")
            print(f"   Updated: {data['counter']['updated_at']}")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'simple':
        simple_increment_test()
    else:
        test_counter_endpoints()