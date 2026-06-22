#!/usr/bin/env python3
"""Add drawing_files column to concentration_entries in all project databases."""

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

        if "drawing_files" in columns:
            print(f"drawing_files already exists in {db_path}")
            return

        print(f"Adding drawing_files to {db_path}...")
        cursor.execute(
            "ALTER TABLE concentration_entries ADD COLUMN drawing_files TEXT"
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
