#!/usr/bin/env python3
"""
Script to create database tables
Run this locally or on Railway to initialize/update the database schema
"""

import os
import sys
from app import app, db

def create_tables():
    """Create all database tables"""
    with app.app_context():
        try:
            # Create all tables defined in the models
            db.create_all()
            print("✅ All database tables created successfully!")
            
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print("\n📊 Existing tables in database:")
            for table in tables:
                print(f"  - {table}")
                
            if 'feedback' in tables:
                print("\n✅ Feedback table confirmed!")
            else:
                print("\n⚠️ Feedback table not found - may need manual creation")
                
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            sys.exit(1)

if __name__ == "__main__":
    print("🔧 Creating database tables...")
    print(f"📍 Database URL: {os.getenv('DATABASE_URL', 'Not set')[:50]}...")
    create_tables()