#!/usr/bin/env python3
"""
Database migration script to add is_manual field to concentration_entries table:
- is_manual: Boolean field to distinguish manually created entries from auto-generated ones
"""

import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Add is_manual field to the concentration_entries table"""
    
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
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(concentration_entries)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"Current columns: {columns}")
        
        # Add is_manual column if it doesn't exist
        if 'is_manual' not in columns:
            print("Adding 'is_manual' column...")
            cursor.execute("ALTER TABLE concentration_entries ADD COLUMN is_manual INTEGER DEFAULT 1")
            print("Successfully added 'is_manual' column")
        else:
            print("'is_manual' column already exists")
        
        # Update existing records to mark auto-generated entries as is_manual = 0
        # Auto-generated entries can be identified by their notes field containing "Auto-populated" or "Auto-updated"
        print("Updating existing records to distinguish manual vs auto-generated entries...")
        
        # First, mark all entries with auto-populated notes as is_manual = 0
        cursor.execute("""
            UPDATE concentration_entries 
            SET is_manual = 0 
            WHERE notes LIKE '%Auto-populated%' OR notes LIKE '%Auto-updated%'
        """)
        
        auto_entries_count = cursor.rowcount
        print(f"Marked {auto_entries_count} auto-generated entries as is_manual = 0")
        
        # Mark remaining entries (which should be manual) as is_manual = 1
        cursor.execute("""
            UPDATE concentration_entries 
            SET is_manual = 1 
            WHERE is_manual != 0 OR (notes NOT LIKE '%Auto-populated%' AND notes NOT LIKE '%Auto-updated%')
        """)
        
        manual_entries_count = cursor.rowcount
        print(f"Marked {manual_entries_count} manual entries as is_manual = 1")
        
        # Commit changes
        conn.commit()
        print("Database migration completed successfully!")
        
        # Verify the new structure and data
        cursor.execute("PRAGMA table_info(concentration_entries)")
        new_columns = [column[1] for column in cursor.fetchall()]
        print(f"New table structure: {new_columns}")
        
        # Count entries by type
        cursor.execute("SELECT COUNT(*) FROM concentration_entries WHERE is_manual = 1")
        manual_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM concentration_entries WHERE is_manual = 0")
        auto_count = cursor.fetchone()[0]
        
        print(f"Total manual entries: {manual_count}")
        print(f"Total auto-generated entries: {auto_count}")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conn.rollback()
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    print("Starting database migration for is_manual field...")
    migrate_database()
    print("Migration script completed.")
