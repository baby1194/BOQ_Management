"""Add submission_breakdown JSON column to calculation and concentration entries."""

from database import project_registry
from database.database import _ensure_submission_breakdown_columns, get_project_engine, init_project_database


if __name__ == "__main__":
    for project in project_registry.list_projects():
        init_project_database(project["id"])
        _ensure_submission_breakdown_columns(get_project_engine(project["id"]))
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
        _ensure_submission_breakdown_columns(engine)
        print(f"Migration completed for {legacy_db}")
