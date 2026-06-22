#!/usr/bin/env python3
"""Migrate calculation_sheets unique key to calculation_sheet_no only."""

from database import project_registry
from database.database import _ensure_calculation_sheet_no_unique, get_project_engine, init_project_database


def migrate_database(db_path) -> None:
    project_id = None
    for project in project_registry.list_projects():
        if project_registry.get_project_db_path(project["id"]) == db_path:
            project_id = project["id"]
            break
    if project_id:
        init_project_database(project_id)
        _ensure_calculation_sheet_no_unique(get_project_engine(project_id))
        print(f"Migration completed for {db_path}")
    else:
        print(f"Could not resolve project id for {db_path}")


if __name__ == "__main__":
    for project in project_registry.list_projects():
        init_project_database(project["id"])
        _ensure_calculation_sheet_no_unique(get_project_engine(project["id"]))
        print(
            "Migration completed for",
            project_registry.get_project_db_path(project["id"]),
        )

    legacy_db = project_registry.LEGACY_DB
    if legacy_db.exists():
        from sqlalchemy import create_engine

        engine = create_engine(
            f"sqlite:///{legacy_db.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        _ensure_calculation_sheet_no_unique(engine)
        print(f"Migration completed for {legacy_db}")
