#!/usr/bin/env python3
"""
Test if psycopg2 is installed correctly
"""

print("🧪 Testing psycopg2 installation...")

try:
    import psycopg2
    print("✅ psycopg2 imported successfully!")
    print(f"   Version: {psycopg2.__version__}")
    
    # Test connection
    try:
        conn = psycopg2.connect(
            host="postgres",
            port=5432,
            database="chrome_extension", 
            user="chrome_user",
            password="chrome_password"
        )
        print("✅ PostgreSQL connection successful!")
        conn.close()
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        
except ImportError as e:
    print(f"❌ Failed to import psycopg2: {e}")
    
    # Check what's installed
    import pkg_resources
    installed_packages = [d.project_name for d in pkg_resources.working_set]
    psycopg_packages = [p for p in installed_packages if 'psycopg' in p.lower()]
    
    print(f"   Found psycopg packages: {psycopg_packages}")
    print(f"   All installed packages: {len(installed_packages)}")