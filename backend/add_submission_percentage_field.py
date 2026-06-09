#!/usr/bin/env python3
"""Add submission_percentage column to concentration_entries in all project databases."""

import sqlite3
from pathlib import Path

from database import project_registry
from database.database import init_project_database


def migrate_database(db_path: Path) -> None:
    if not db_path.exists():
        print(f"Skipping missing database: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(concentration_entries)")
        columns = [column[1] for column in cursor.fetchall()]

        if "submission_percentage" in columns:
            print(f"submission_percentage already exists in {db_path}")
            return

        print(f"Adding submission_percentage to {db_path}...")
        cursor.execute(
            "ALTER TABLE concentration_entries "
            "ADD COLUMN submission_percentage REAL DEFAULT 100.0"
        )
        cursor.execute(
            """
            UPDATE concentration_entries
            SET submission_percentage = CASE
                WHEN estimated_quantity > 0
                THEN (quantity_submitted / estimated_quantity) * 100.0
                ELSE 100.0
            END
            """
        )
        conn.commit()
        print(f"Migration completed for {db_path}")
    except sqlite3.Error as exc:
        print(f"Database error for {db_path}: {exc}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    for project in project_registry.list_projects():
        init_project_database(project["id"])
        migrate_database(project_registry.get_project_db_path(project["id"]))

    legacy_db = project_registry.LEGACY_DB
    if legacy_db.exists():
        migrate_database(legacy_db)
