#!/usr/bin/env python3
"""
Script to add the contract_quantity_updates and boq_item_quantity_updates tables to existing databases.
This script safely adds the new tables without affecting existing data.
"""

import sqlite3
import os
from pathlib import Path

def add_contract_updates_tables():
    """Add contract updates tables to the database"""
    
    # Database path
    db_path = Path("database/boq_system.db")
    
    if not db_path.exists():
        print("Database not found. Creating new database with contract updates tables...")
        # Import models to create all tables
        from models import models
        from database.database import engine
        models.Base.metadata.create_all(bind=engine)
        print("Database created successfully!")
        return
    
    print(f"Adding contract updates tables to existing database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if contract_quantity_updates table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='contract_quantity_updates'
        """)
        
        if cursor.fetchone():
            print("contract_quantity_updates table already exists!")
        else:
            # Create contract_quantity_updates table
            cursor.execute("""
                CREATE TABLE contract_quantity_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_index INTEGER NOT NULL UNIQUE,
                    update_name VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("contract_quantity_updates table created successfully!")
        
        # Check if boq_item_quantity_updates table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='boq_item_quantity_updates'
        """)
        
        if cursor.fetchone():
            print("boq_item_quantity_updates table already exists!")
        else:
            # Create boq_item_quantity_updates table
            cursor.execute("""
                CREATE TABLE boq_item_quantity_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    boq_item_id INTEGER NOT NULL,
                    contract_update_id INTEGER NOT NULL,
                    updated_contract_quantity FLOAT NOT NULL,
                    updated_contract_sum FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (boq_item_id) REFERENCES boq_items (id),
                    FOREIGN KEY (contract_update_id) REFERENCES contract_quantity_updates (id),
                    UNIQUE(boq_item_id, contract_update_id)
                )
            """)
            print("boq_item_quantity_updates table created successfully!")
        
        # Commit changes
        conn.commit()
        
        # Verify table creation
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%contract%'")
        tables = cursor.fetchall()
        print(f"Contract-related tables found: {[table[0] for table in tables]}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error creating contract updates tables: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise

if __name__ == "__main__":
    print("Adding contract updates tables to database...")
    add_contract_updates_tables()
    print("Done!")

