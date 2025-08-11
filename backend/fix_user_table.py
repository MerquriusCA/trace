#!/usr/bin/env python3
"""
Fix user table to handle long picture URLs
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fix_user_table():
    """Fix the user table to handle long picture URLs"""
    try:
        from app import app, db
        
        with app.app_context():
            # Drop and recreate tables (for development only)
            print("🔧 Dropping and recreating tables...")
            db.drop_all()
            db.create_all()
            print("✅ Tables recreated successfully!")
            
            # Show created tables
            from sqlalchemy import text
            result = db.session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result]
            
            print("📋 Tables created:")
            for table in tables:
                print(f"   - {table}")
                
            # Show user table structure
            result = db.session.execute(text("SELECT column_name, data_type, character_maximum_length FROM information_schema.columns WHERE table_name = 'user' ORDER BY ordinal_position"))
            print("\n📊 User table structure:")
            for row in result:
                col_name, data_type, max_length = row
                length_info = f"({max_length})" if max_length else ""
                print(f"   - {col_name}: {data_type}{length_info}")
                
    except Exception as e:
        print(f"❌ Error fixing user table: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = fix_user_table()
    if success:
        print("\n🎉 User table fixed successfully!")
        print("   You can now sign in with Google without URL length issues.")
    else:
        print("\n❌ Failed to fix user table.")