#!/usr/bin/env python3
"""
Test script for cnter endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_cnter_endpoints():
    """Test all cnter endpoints"""
    print("🧪 Testing Cnter Endpoints")
    print("=" * 40)
    
    # Test 1: Increment default cnter
    print("\n1️⃣ Testing cnter increment (default):")
    try:
        response = requests.post(f"{BASE_URL}/api/cnter/increment", 
                               json={}, 
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data['message']}")
            print(f"   Count: {data['cnter']['count']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Increment named cnter
    print("\n2️⃣ Testing cnter increment (named 'test'):")
    try:
        response = requests.post(f"{BASE_URL}/api/cnter/increment", 
                               json={"name": "test"}, 
                               headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data['message']}")
            print(f"   Count: {data['cnter']['count']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Increment multiple times
    print("\n3️⃣ Testing multiple increments:")
    for i in range(3):
        try:
            response = requests.post(f"{BASE_URL}/api/cnter/increment", 
                                   json={"name": "rapid"}, 
                                   headers={'Content-Type': 'application/json'})
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Increment {i+1}: Count = {data['cnter']['count']}")
            else:
                print(f"❌ Failed increment {i+1}: {response.status_code}")
        except Exception as e:
            print(f"❌ Error on increment {i+1}: {e}")
        
        time.sleep(0.1)  # Small delay
    
    # Test 4: Get specific cnter
    print("\n4️⃣ Testing get cnter:")
    try:
        response = requests.get(f"{BASE_URL}/api/cnter/test")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cnter 'test': {data['cnter']['count']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: Get all cnters
    print("\n5️⃣ Testing get all cnters:")
    try:
        response = requests.get(f"{BASE_URL}/api/cnters")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['total']} cnters:")
            for cnter in data['cnters']:
                print(f"   - {cnter['name']}: {cnter['count']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 6: Test non-existent cnter
    print("\n6️⃣ Testing non-existent cnter:")
    try:
        response = requests.get(f"{BASE_URL}/api/cnter/nonexistent")
        
        if response.status_code == 404:
            print("✅ Correctly returned 404 for non-existent cnter")
        else:
            print(f"❌ Expected 404, got {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🎉 Cnter endpoint tests completed!")

def simple_increment_test():
    """Simple test that just increments a cnter"""
    print("🔥 Simple Cnter Increment Test")
    print("=" * 35) 
    
    try:
        response = requests.post(f"{BASE_URL}/api/cnter/increment")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Cnter incremented!")
            print(f"   Name: {data['cnter']['name']}")
            print(f"   Count: {data['cnter']['count']}")
            print(f"   Updated: {data['cnter']['updated_at']}")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def compare_counter_and_cnter():
    """Compare counter and cnter endpoints side by side"""
    print("🔄 Comparing Counter vs Cnter")
    print("=" * 35)
    
    # Test counter
    try:
        response = requests.post(f"{BASE_URL}/api/counter/increment", 
                               json={"name": "compare"})
        if response.status_code == 200:
            counter_data = response.json()
            print(f"✅ Counter: {counter_data['counter']['count']}")
        else:
            print(f"❌ Counter failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Counter error: {e}")
    
    # Test cnter
    try:
        response = requests.post(f"{BASE_URL}/api/cnter/increment", 
                               json={"name": "compare"})
        if response.status_code == 200:
            cnter_data = response.json()
            print(f"✅ Cnter: {cnter_data['cnter']['count']}")
        else:
            print(f"❌ Cnter failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Cnter error: {e}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'simple':
            simple_increment_test()
        elif sys.argv[1] == 'compare':
            compare_counter_and_cnter()
        else:
            test_cnter_endpoints()
    else:
        test_cnter_endpoints()