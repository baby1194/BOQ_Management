#!/usr/bin/env python3
"""
Script to add subsection_info table to existing database.
This table stores descriptions for subsections that users can edit.
"""

import sqlite3
import os
from pathlib import Path

def add_subsection_info_table():
    """Add subsection_info table to the database"""
    
    # Database path
    db_path = Path("database/boq_management.db")
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        print("Please run the main application first to create the database.")
        return
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='subsection_info'
        """)
        
        if cursor.fetchone():
            print("subsection_info table already exists.")
            return
        
        # Create subsection_info table
        cursor.execute("""
            CREATE TABLE subsection_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subsection TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index on subsection for faster lookups
        cursor.execute("""
            CREATE INDEX idx_subsection_info_subsection 
            ON subsection_info(subsection)
        "")
        
        # Commit changes
        conn.commit()
        
        print("✅ subsection_info table created successfully!")
        print("   - Stores subsection descriptions")
        print("   - Has unique constraint on subsection")
        print("   - Includes created_at and updated_at timestamps")
        
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Adding subsection_info table to database...")
    add_subsection_info_table()
    print("Done!")
