"""
Add invoice fields to ProjectInfo table.

This script adds 4 new columns to the project_info table:
- invoice_no_submitted_qty
- invoice_date_submitted_qty
- invoice_no_approved_signed_qty
- invoice_date_approved_signed_qty
"""

import sqlite3
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_invoice_fields():
    """Add invoice fields to the project_info table."""
    db_path = Path("database/boq_system.db")
    
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(project_info)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            'invoice_no_submitted_qty',
            'invoice_date_submitted_qty', 
            'invoice_no_approved_signed_qty',
            'invoice_date_approved_signed_qty'
        ]
        
        columns_to_add = [col for col in new_columns if col not in columns]
        
        if not columns_to_add:
            logger.info("All invoice fields already exist in the project_info table.")
            return True
        
        # Add the new columns
        for column in columns_to_add:
            if 'date' in column:
                # Date columns
                sql = f"ALTER TABLE project_info ADD COLUMN {column} DATETIME"
            else:
                # String columns
                sql = f"ALTER TABLE project_info ADD COLUMN {column} VARCHAR(100)"
            
            logger.info(f"Adding column: {column}")
            cursor.execute(sql)
        
        # Commit the changes
        conn.commit()
        logger.info(f"Successfully added {len(columns_to_add)} invoice fields to project_info table.")
        
        # Verify the columns were added
        cursor.execute("PRAGMA table_info(project_info)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        
        logger.info("Current project_info table columns:")
        for col in updated_columns:
            logger.info(f"  - {col}")
        
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logger.info("Starting to add invoice fields to project_info table...")
    success = add_invoice_fields()
    
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
        exit(1)
