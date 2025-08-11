#!/usr/bin/env python3
"""
Test script for Docker setup validation
"""

import subprocess
import sys
import time
import requests
import json

def run_command(cmd, description):
    """Run a command and return success status"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ {description}")
            return True, result.stdout.strip()
        else:
            print(f"❌ {description}")
            print(f"   Error: {result.stderr.strip()}")
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} (timeout)")
        return False, "Command timed out"
    except Exception as e:
        print(f"❌ {description}")
        print(f"   Exception: {e}")
        return False, str(e)

def test_http_endpoint(url, description, timeout=10):
    """Test HTTP endpoint"""
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            print(f"✅ {description} (Status: {response.status_code})")
            return True, response.json() if 'application/json' in response.headers.get('content-type', '') else response.text
        else:
            print(f"❌ {description} (Status: {response.status_code})")
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.RequestException as e:
        print(f"❌ {description}")
        print(f"   Error: {e}")
        return False, str(e)

def main():
    """Run all tests"""
    print("🧪 Docker Environment Test Suite")
    print("=" * 50)
    
    tests = []
    
    # Test 1: Docker availability
    print("\n🔍 Testing Docker Environment:")
    success, output = run_command("docker --version", "Docker installation")
    tests.append(("Docker Installation", success))
    
    success, output = run_command("docker-compose --version", "Docker Compose")
    tests.append(("Docker Compose", success))
    
    # Test 2: Container status
    print("\n🐳 Testing Container Status:")
    success, output = run_command("docker-compose ps", "Container status check")
    tests.append(("Container Status", success))
    
    if success and 'chrome_ext_app' in output:
        print("   📱 Flask app container detected")
    if success and 'chrome_ext_postgres' in output:
        print("   🐘 PostgreSQL container detected")
    if success and 'chrome_ext_pgadmin' in output:
        print("   🖥️  pgAdmin container detected")
    
    # Test 3: Service endpoints
    print("\n🌐 Testing Service Endpoints:")
    
    # Wait a moment for services to be ready
    print("⏳ Waiting for services to be ready...")
    time.sleep(5)
    
    success, data = test_http_endpoint("http://localhost:8000/api/health", "Flask app health check")
    tests.append(("Flask Health Check", success))
    
    if success:
        try:
            health_data = data if isinstance(data, dict) else json.loads(data)
            db_status = health_data.get('services', {}).get('database', {}).get('status')
            stripe_status = health_data.get('services', {}).get('stripe', {}).get('status')
            
            print(f"   📊 Database: {db_status}")
            print(f"   💳 Stripe: {stripe_status}")
        except:
            print("   📊 Health check response received")
    
    success, data = test_http_endpoint("http://localhost:8000/api/test", "Flask test endpoint")
    tests.append(("Flask Test Endpoint", success))
    
    success, data = test_http_endpoint("http://localhost:5050", "pgAdmin interface", timeout=15)
    tests.append(("pgAdmin Interface", success))
    
    # Test 4: Database connection
    print("\n🗄️ Testing Database Connection:")
    success, output = run_command(
        'docker-compose exec -T postgres psql -U chrome_user -d chrome_extension -c "SELECT 1;"',
        "PostgreSQL connection test"
    )
    tests.append(("PostgreSQL Connection", success))
    
    # Test 5: App database connectivity
    success, output = run_command(
        'docker-compose exec -T app python -c "from app import db; from sqlalchemy import text; db.session.execute(text(\'SELECT 1\')); print(\'Database connected!\')"',
        "Flask app database connection"
    )
    tests.append(("Flask Database Connection", success))
    
    # Summary
    print("\n📋 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test_name, success in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your Docker environment is ready!")
        print("\n🚀 Access your services:")
        print("   📱 Flask App:  http://localhost:8000")
        print("   🖥️  pgAdmin:    http://localhost:5050")
        print("   🗄️  PostgreSQL: localhost:5433")
        print("\n💡 Try the Chrome extension now!")
    else:
        print(f"\n⚠️ Some tests failed. Please check the Docker setup.")
        print("💡 Try: docker-compose down && docker-compose up --build")
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())