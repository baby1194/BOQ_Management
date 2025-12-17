#!/usr/bin/env python3
"""
Database migration script to add internal fields to boq_items table:
- internal_field_1: String column for internal use (max 255 characters)
- internal_field_2: String column for internal use (max 255 characters)

These fields are for internal tracking and are not displayed in standard reports.
"""

import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Add internal_field_1 and internal_field_2 fields to the boq_items table"""
    
    # Get the database path
    db_path = Path("database/boq_system.db")
    
    if not db_path.exists():
        print("Database file not found. Please run the main application first to create the database.")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Connected to database successfully.")
        
        # Check if boq_items table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='boq_items'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("boq_items table does not exist. Please create it first.")
            conn.close()
            return
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(boq_items)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"Current columns in boq_items: {columns}")
        
        # Add internal_field_1 column if it doesn't exist
        if 'internal_field_1' not in columns:
            print("Adding 'internal_field_1' column...")
            cursor.execute("ALTER TABLE boq_items ADD COLUMN internal_field_1 VARCHAR(255)")
            conn.commit()
            print("✓ Successfully added 'internal_field_1' column")
        else:
            print("✓ 'internal_field_1' column already exists")
        
        # Add internal_field_2 column if it doesn't exist
        if 'internal_field_2' not in columns:
            print("Adding 'internal_field_2' column...")
            cursor.execute("ALTER TABLE boq_items ADD COLUMN internal_field_2 VARCHAR(255)")
            conn.commit()
            print("✓ Successfully added 'internal_field_2' column")
        else:
            print("✓ 'internal_field_2' column already exists")
        
        # Verify the columns were added
        cursor.execute("PRAGMA table_info(boq_items)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        
        if 'internal_field_1' in updated_columns and 'internal_field_2' in updated_columns:
            print("\n✅ Migration completed successfully!")
            print("   - internal_field_1: VARCHAR(255), nullable")
            print("   - internal_field_2: VARCHAR(255), nullable")
        else:
            print("\n⚠️  Warning: Some columns may not have been added correctly.")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
            conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Adding internal fields to BOQ items table")
    print("=" * 60)
    migrate_database()
    print("=" * 60)

