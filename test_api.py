#!/usr/bin/env python3
"""
Test script for Trace API endpoints
"""
import requests
import json
import sys

# Your Railway deployment URL
API_BASE_URL = "https://trace-production-79d5.up.railway.app"

def test_health():
    """Test the health endpoint"""
    print("🔍 Testing /health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health Check Response:")
            print(json.dumps(data, indent=2))
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_api_test():
    """Test the /api/test endpoint"""
    print("\n🔍 Testing /api/test endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/test")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Test Response:")
            print(json.dumps(data, indent=2))
            return True
        else:
            print(f"❌ API test failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_summarize_unauthorized():
    """Test that summarize endpoint requires authentication"""
    print("\n🔍 Testing /api/summarize (should require auth)...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/summarize",
            json={"url": "https://example.com", "text": "Test content"}
        )
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("✅ Correctly requires authentication")
            return True
        else:
            print(f"⚠️ Unexpected status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print(f"🚀 Testing Trace API at: {API_BASE_URL}")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("API Test", test_api_test()))
    results.append(("Auth Check", test_summarize_unauthorized()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY:")
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())