#!/usr/bin/env python3
"""
Script to add the project_info table to existing databases.
This script safely adds the new table without affecting existing data.
"""

import sqlite3
import os
from pathlib import Path

def add_project_info_table():
    """Add project_info table to the database"""
    
    # Database path
    db_path = Path("database/boq_system.db")
    
    if not db_path.exists():
        print("Database not found. Creating new database with project_info table...")
        # Import models to create all tables
        from models import models
        from database.database import engine
        models.Base.metadata.create_all(bind=engine)
        print("Database created successfully!")
        return
    
    print(f"Adding project_info table to existing database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='project_info'
        """)
        
        if cursor.fetchone():
            print("project_info table already exists!")
            conn.close()
            return
        
        # Create project_info table
        cursor.execute("""
            CREATE TABLE project_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name VARCHAR(200),
                main_contractor_name VARCHAR(200),
                subcontractor_name VARCHAR(200),
                developer_name VARCHAR(200),
                contract_no VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default record
        cursor.execute("""
            INSERT INTO project_info (
                project_name, 
                main_contractor_name, 
                subcontractor_name, 
                developer_name, 
                contract_no
            ) VALUES (?, ?, ?, ?, ?)
        """, (None, None, None, None, None))
        
        # Commit changes
        conn.commit()
        print("project_info table created successfully!")
        print("Default record inserted.")
        
        # Verify table creation
        cursor.execute("SELECT * FROM project_info")
        result = cursor.fetchone()
        if result:
            print(f"Verified: Table contains {len(result)} columns")
        
        conn.close()
        
    except Exception as e:
        print(f"Error creating project_info table: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise

if __name__ == "__main__":
    print("Adding project_info table to database...")
    add_project_info_table()
    print("Done!")

