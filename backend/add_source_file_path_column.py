#!/usr/bin/env python3
"""
Database migration script to add source_file_path field to calculation_sheets table:
- source_file_path: String column for storing the original file path when imported
"""

import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Add source_file_path field to the calculation_sheets table"""
    
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
        
        # Check if calculation_sheets table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='calculation_sheets'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("calculation_sheets table does not exist. Please create it first.")
            conn.close()
            return
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(calculation_sheets)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"Current columns in calculation_sheets: {columns}")
        
        # Add source_file_path column if it doesn't exist
        if 'source_file_path' not in columns:
            print("Adding 'source_file_path' column...")
            cursor.execute("ALTER TABLE calculation_sheets ADD COLUMN source_file_path VARCHAR(500)")
            conn.commit()
            print("✓ Successfully added 'source_file_path' column")
        else:
            print("✓ 'source_file_path' column already exists")
        
        conn.close()
        print("Migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    migrate_database()

