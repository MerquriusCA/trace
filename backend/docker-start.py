#!/usr/bin/env python3
"""
Docker startup script for Chrome Extension Backend
Handles initialization and starts the Flask app
"""

import os
import time
import subprocess
import sys

# Don't import app here - wait until PostgreSQL is ready

def wait_for_postgres():
    """Wait for PostgreSQL to be ready using pg_isready"""
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            # Use pg_isready to check if PostgreSQL is accepting connections
            result = subprocess.run([
                'pg_isready', '-h', 'postgres', '-p', '5432', '-U', 'chrome_user'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                print(f"✅ PostgreSQL is ready!")
                return True
            else:
                if attempt < max_attempts - 1:
                    print(f"⏳ Waiting for PostgreSQL... ({attempt + 1}/{max_attempts})")
                    time.sleep(2)
                else:
                    print(f"❌ PostgreSQL not ready after {max_attempts} attempts")
                    return False
        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"⏳ Waiting for PostgreSQL... ({attempt + 1}/{max_attempts}) - {e}")
                time.sleep(2)
            else:
                print(f"❌ Failed to check PostgreSQL after {max_attempts} attempts: {e}")
                return False
    return False

def initialize_database():
    """Initialize database tables"""
    try:
        print("🔧 Initializing database tables...")
        
        # Import app after PostgreSQL is ready
        from app import app, db
        
        with app.app_context():
            db.create_all()
            
            # Verify tables were created
            from sqlalchemy import text
            result = db.session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result]
            
            if tables:
                print(f"✅ Database tables created: {', '.join(tables)}")
            else:
                print("⚠️ No tables found after creation")
                
            return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def main():
    """Main startup function"""
    print("🐳 Chrome Extension Backend - Docker Startup")
    print("=" * 50)
    
    # Wait for PostgreSQL
    print("🔍 Checking PostgreSQL connection...")
    if not wait_for_postgres():
        print("❌ PostgreSQL connection failed. Exiting.")
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        print("❌ Database initialization failed. Exiting.")
        sys.exit(1)
    
    print("✅ Startup initialization complete!")
    print("🚀 Starting Flask development server...")
    print("=" * 50)
    
    # Start Flask app with hot reload
    try:
        # Import app here after all checks are done
        from app import app
        
        app.run(
            host='0.0.0.0',
            port=8000,
            debug=True,
            use_reloader=True,
            use_debugger=True,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()