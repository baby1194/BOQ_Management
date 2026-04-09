#!/usr/bin/env python3
"""
Add display_order to boq_items for BOQ table row ordering (drag-and-drop).
Backfills existing rows by id order.
"""

import sqlite3
from pathlib import Path


def migrate_database():
    db_path = Path("database/boq_system.db")
    if not db_path.exists():
        print("Database file not found. Create or locate boq_system.db first.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(boq_items)")
        columns = [c[1] for c in cursor.fetchall()]

        if "display_order" not in columns:
            print("Adding display_order column...")
            cursor.execute(
                "ALTER TABLE boq_items ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0"
            )
            print("Backfilling display_order by id...")
            cursor.execute("SELECT id FROM boq_items ORDER BY id")
            ids = [r[0] for r in cursor.fetchall()]
            for i, item_id in enumerate(ids):
                cursor.execute(
                    "UPDATE boq_items SET display_order = ? WHERE id = ?",
                    (i, item_id),
                )
            conn.commit()
            print(f"Set display_order for {len(ids)} row(s).")
        else:
            print("display_order column already exists; skipping add.")

        conn.commit()
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()
