#!/usr/bin/env python3
"""
Simple migration runner for adding preference columns
Usage: python migrate_preferences.py
"""

import os
import sys

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def run_migration():
    """Run the preference columns migration"""
    
    print("🚀 Running preference columns migration...")
    
    with app.app_context():
        try:
            # Create all tables first (in case they don't exist)
            db.create_all()
            print("✅ Database tables created/verified")
            
            # Check existing columns
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user'
            """))
            existing_columns = [row[0] for row in result]
            print(f"📋 Existing columns: {existing_columns}")
            
            # Add missing preference columns
            migrations = []
            
            if 'summary_style' not in existing_columns:
                migrations.append({
                    'name': 'summary_style',
                    'sql': 'ALTER TABLE "user" ADD COLUMN summary_style VARCHAR(20) DEFAULT \'eli8\''
                })
            
            if 'auto_summarize_enabled' not in existing_columns:
                migrations.append({
                    'name': 'auto_summarize_enabled', 
                    'sql': 'ALTER TABLE "user" ADD COLUMN auto_summarize_enabled BOOLEAN DEFAULT false'
                })
            
            if 'notifications_enabled' not in existing_columns:
                migrations.append({
                    'name': 'notifications_enabled',
                    'sql': 'ALTER TABLE "user" ADD COLUMN notifications_enabled BOOLEAN DEFAULT true'
                })
            
            if not migrations:
                print("✅ All preference columns already exist - no migration needed!")
                return True
            
            # Execute migrations
            for migration in migrations:
                print(f"🔧 Adding column: {migration['name']}")
                print(f"📝 SQL: {migration['sql']}")
                
                try:
                    db.session.execute(text(migration['sql']))
                    db.session.commit()
                    print(f"✅ Successfully added {migration['name']}")
                except Exception as e:
                    print(f"❌ Error adding {migration['name']}: {e}")
                    db.session.rollback()
                    return False
            
            # Verify final state
            result = db.session.execute(text("""
                SELECT column_name, data_type, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'user' 
                  AND column_name IN ('summary_style', 'auto_summarize_enabled', 'notifications_enabled')
                ORDER BY column_name
            """))
            
            print("\n📋 Final column state:")
            for row in result:
                print(f"   {row[0]}: {row[1]} (default: {row[2]})")
            
            print("\n🎉 Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)