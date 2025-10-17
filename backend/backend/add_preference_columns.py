#!/usr/bin/env python3
"""
Migration script to add user preference columns to existing database
Run this script to add the new preference columns to the User table
"""

import os
import sys
from sqlalchemy import text
from app import app, db

def add_preference_columns():
    """Add preference columns to User table if they don't exist"""
    
    print("🔄 Checking and adding preference columns to User table...")
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]
            
            print(f"📋 Existing columns: {columns}")
            
            # Add missing columns
            columns_to_add = []
            
            if 'summary_style' not in columns:
                columns_to_add.append("ADD COLUMN summary_style VARCHAR(20) DEFAULT 'eli8'")
                
            if 'auto_summarize_enabled' not in columns:
                columns_to_add.append("ADD COLUMN auto_summarize_enabled BOOLEAN DEFAULT false")
                
            if 'notifications_enabled' not in columns:
                columns_to_add.append("ADD COLUMN notifications_enabled BOOLEAN DEFAULT true")
            
            if not columns_to_add:
                print("✅ All preference columns already exist!")
                return True
                
            print(f"🔧 Adding {len(columns_to_add)} new columns...")
            
            # Execute ALTER TABLE statements
            for alter_statement in columns_to_add:
                full_statement = f"ALTER TABLE \"user\" {alter_statement}"
                print(f"📝 Executing: {full_statement}")
                
                try:
                    db.session.execute(text(full_statement))
                    db.session.commit()
                    print(f"✅ Successfully added column")
                except Exception as e:
                    print(f"❌ Error adding column: {e}")
                    db.session.rollback()
                    return False
            
            # Verify columns were added
            inspector = db.inspect(db.engine)
            new_columns = [col['name'] for col in inspector.get_columns('user')]
            print(f"📋 Updated columns: {new_columns}")
            
            print("🎉 Preference columns added successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    print("🚀 Starting preference columns migration...")
    success = add_preference_columns()
    
    if success:
        print("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        print("❌ Migration failed!")
        sys.exit(1)