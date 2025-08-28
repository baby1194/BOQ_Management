#!/usr/bin/env python3
"""
Database migration script to add new columns to BOQ items table:
- system: String column for system information
- approved_signed_quantity: Float column for approved signed quantity (default 0)
- approved_signed_total: Float column for approved signed total (default 0)
"""

import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Add new columns to the BOQ items table"""
    
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
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(boq_items)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"Current columns: {columns}")
        
        # Add new columns if they don't exist
        if 'system' not in columns:
            print("Adding 'system' column...")
            cursor.execute("ALTER TABLE boq_items ADD COLUMN system TEXT")
            print("✓ Added 'system' column")
        else:
            print("✓ 'system' column already exists")
        
        if 'approved_signed_quantity' not in columns:
            print("Adding 'approved_signed_quantity' column...")
            cursor.execute("ALTER TABLE boq_items ADD COLUMN approved_signed_quantity REAL DEFAULT 0.0")
            print("✓ Added 'approved_signed_quantity' column")
        else:
            print("✓ 'approved_signed_quantity' column already exists")
        
        if 'approved_signed_total' not in columns:
            print("Adding 'approved_signed_total' column...")
            cursor.execute("ALTER TABLE boq_items ADD COLUMN approved_signed_total REAL DEFAULT 0.0")
            print("✓ Added 'approved_signed_total' column")
        else:
            print("✓ 'approved_signed_total' column already exists")
        
        # Update existing records to set default values for approved_signed_total
        print("Updating existing records...")
        cursor.execute("""
            UPDATE boq_items 
            SET approved_signed_total = approved_signed_quantity * price 
            WHERE approved_signed_total IS NULL OR approved_signed_total = 0
        """)
        
        updated_count = cursor.rowcount
        print(f"✓ Updated {updated_count} existing records")
        
        # Commit changes
        conn.commit()
        print("✓ Database migration completed successfully!")
        
        # Verify the new structure
        cursor.execute("PRAGMA table_info(boq_items)")
        new_columns = [column[1] for column in cursor.fetchall()]
        print(f"New table structure: {new_columns}")
        
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
    print("Starting database migration...")
    migrate_database()
    print("Migration script completed.")
