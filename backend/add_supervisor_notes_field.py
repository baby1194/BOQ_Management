#!/usr/bin/env python3
"""Add supervisor_notes column to concentration_entries (SQLite)."""

import sqlite3
from pathlib import Path


def migrate_database():
    db_path = Path("database/boq_system.db")
    if not db_path.exists():
        print("Database file not found. Run the app once to create it.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(concentration_entries)")
        columns = [column[1] for column in cursor.fetchall()]
        if "supervisor_notes" not in columns:
            print("Adding supervisor_notes column...")
            cursor.execute(
                "ALTER TABLE concentration_entries ADD COLUMN supervisor_notes TEXT"
            )
            conn.commit()
            print("Done.")
        else:
            print("supervisor_notes column already exists.")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()
