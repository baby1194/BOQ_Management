#!/usr/bin/env python3
"""
Database migration script to change column types:
- serial_number: REAL -> INTEGER
- structure: REAL -> INTEGER
"""

import sqlite3
import os
from pathlib import Path

def migrate_column_types():
    """Change column types from REAL to INTEGER for serial_number and structure"""
    
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
        
        # Check current column types
        cursor.execute("PRAGMA table_info(boq_items)")
        columns = cursor.fetchall()
        
        print("Current column types:")
        for col in columns:
            if col[1] in ['serial_number', 'structure']:
                print(f"  {col[1]}: {col[2]} (currently {col[2]})")
        
        # SQLite doesn't support ALTER COLUMN TYPE directly, so we need to recreate the table
        print("\nStarting column type migration...")
        
        # Get all data from the current table
        cursor.execute("SELECT * FROM boq_items")
        all_data = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(boq_items)")
        column_info = cursor.fetchall()
        column_names = [col[1] for col in column_info]
        
        print(f"Found {len(all_data)} records to migrate")
        print(f"Columns: {column_names}")
        
        # Create new table with correct column types
        create_table_sql = """
        CREATE TABLE boq_items_new (
            id INTEGER PRIMARY KEY,
            serial_number INTEGER,
            structure INTEGER,
            system TEXT,
            section_number TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL,
            unit TEXT NOT NULL,
            original_contract_quantity REAL NOT NULL,
            price REAL NOT NULL,
            total_contract_sum REAL NOT NULL,
            estimated_quantity REAL DEFAULT 0.0,
            quantity_submitted REAL DEFAULT 0.0,
            internal_quantity REAL DEFAULT 0.0,
            approved_by_project_manager REAL DEFAULT 0.0,
            total_estimate REAL DEFAULT 0.0,
            total_submitted REAL DEFAULT 0.0,
            internal_total REAL DEFAULT 0.0,
            total_approved_by_project_manager REAL DEFAULT 0.0,
            approved_signed_quantity REAL DEFAULT 0.0,
            approved_signed_total REAL DEFAULT 0.0,
            notes TEXT,
            subsection TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """
        
        cursor.execute(create_table_sql)
        print("✓ Created new table with correct column types")
        
        # Insert all data into the new table
        placeholders = ', '.join(['?' for _ in column_names])
        insert_sql = f"INSERT INTO boq_items_new ({', '.join(column_names)}) VALUES ({placeholders})"
        
        cursor.executemany(insert_sql, all_data)
        print(f"✓ Migrated {len(all_data)} records to new table")
        
        # Drop old table and rename new one
        cursor.execute("DROP TABLE boq_items")
        cursor.execute("ALTER TABLE boq_items_new RENAME TO boq_items")
        print("✓ Replaced old table with new one")
        
        # Recreate indexes
        cursor.execute("CREATE INDEX ix_boq_items_section_number ON boq_items (section_number)")
        cursor.execute("CREATE INDEX ix_boq_items_subsection ON boq_items (subsection)")
        print("✓ Recreated indexes")
        
        # Verify the new structure
        cursor.execute("PRAGMA table_info(boq_items)")
        new_columns = cursor.fetchall()
        
        print("\nNew table structure:")
        for col in new_columns:
            if col[1] in ['serial_number', 'structure']:
                print(f"  {col[1]}: {col[2]} ✓")
        
        # Commit changes
        conn.commit()
        print("\n✓ Database migration completed successfully!")
        
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
    print("Starting column type migration...")
    migrate_column_types()
    print("Migration script completed.")

