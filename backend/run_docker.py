#!/usr/bin/env python3
"""
Development script to run Flask app with Docker PostgreSQL
"""

import os
import sys
import subprocess
import time
from dotenv import load_dotenv

def check_docker():
    """Check if Docker is running"""
    try:
        subprocess.run(['docker', '--version'], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def start_docker_services():
    """Start Docker Compose services"""
    print("🐳 Starting Docker services...")
    try:
        # Start services in detached mode
        subprocess.run(['docker-compose', 'up', '-d'], check=True)
        print("✅ Docker services started")
        
        # Wait for PostgreSQL to be ready
        print("⏳ Waiting for PostgreSQL to be ready...")
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                result = subprocess.run([
                    'docker-compose', 'exec', '-T', 'postgres', 
                    'pg_isready', '-U', 'chrome_user', '-d', 'chrome_extension'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✅ PostgreSQL is ready!")
                    return True
                    
            except subprocess.CalledProcessError:
                pass
                
            time.sleep(1)
            print(f"   Attempt {attempt + 1}/{max_attempts}...")
        
        print("❌ PostgreSQL failed to start within timeout")
        return False
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start Docker services: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Chrome Extension Backend - Docker Development Mode")
    print("=" * 60)
    
    # Check if Docker is available
    if not check_docker():
        print("❌ Docker is not installed or not running")
        print("   Please install Docker Desktop and make sure it's running")
        sys.exit(1)
    
    # Start Docker services
    if not start_docker_services():
        print("❌ Failed to start Docker services")
        sys.exit(1)
    
    # Load environment variables
    load_dotenv()
    
    print("\n📊 Service Information:")
    print("   PostgreSQL: http://localhost:5433")
    print("   pgAdmin:    http://localhost:5050")
    print("     Email:    admin@example.com")  
    print("     Password: admin")
    print("   Flask App:  http://localhost:8000")
    
    print("\n🔧 Starting Flask development server...")
    print("   Press Ctrl+C to stop\n")
    
    # Start Flask app
    try:
        from app import app
        app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=True)
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
    except ImportError as e:
        print(f"❌ Failed to import Flask app: {e}")
        print("   Make sure you have installed the requirements:")
        print("   pip install -r requirements.txt")
        sys.exit(1)

if __name__ == '__main__':
    main()