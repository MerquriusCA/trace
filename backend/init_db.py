#!/usr/bin/env python3
"""
Initialize database for deployment
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def initialize_database():
    """Initialize database with tables"""
    database_url = os.getenv('DATABASE_URL', '')
    is_railway = bool(os.getenv('RAILWAY_ENVIRONMENT_ID'))
    
    # Skip database initialization during Railway build phase
    # Railway's internal DNS (*.railway.internal) is only available at runtime, not build time
    if is_railway and 'railway.internal' in database_url:
        print("🚂 Railway build phase detected")
        print("⏭️  Skipping database initialization during build")
        print("📝 Tables will be created on first app startup")
        print("✅ Build phase completed successfully")
        return
    
    # For other environments or Railway with external DB URL, proceed with initialization
    try:
        # Import app after environment check
        from app import app, db
        
        with app.app_context():
            if database_url.startswith('postgresql://') or database_url.startswith('postgres://'):
                print("🐘 Initializing PostgreSQL database...")
            elif database_url.startswith('sqlite://'):
                print("🗄️ Initializing SQLite database...")
            else:
                print("🗄️ Initializing database...")
            
            # Create all tables
            print("🔧 Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully!")
            
            # Show created tables
            print("📋 Tables created:")
            for table in db.metadata.tables:
                print(f"   - {table}")
                
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")
        print(f"⚠️  Error type: {type(e).__name__}")
        
        # Don't fail the build for connection issues on Railway
        if is_railway and "could not translate host name" in str(e):
            print("\n📝 Railway internal DNS not available during build phase")
            print("✅ This is expected - tables will be created at runtime")
            return
        
        # For other errors, fail the build
        print(f"❌ DATABASE_URL: {database_url[:50]}...")
        sys.exit(1)

if __name__ == '__main__':
    initialize_database()