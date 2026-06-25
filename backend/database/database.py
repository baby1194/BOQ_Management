from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from fastapi import Header, HTTPException, Depends, Query
from pathlib import Path
from typing import Dict, Generator
import threading

from database import project_registry

Base = declarative_base()

_lock = threading.RLock()
_system_engine = None
_system_session_factory = None
_project_engines: Dict[str, object] = {}
_project_session_factories: Dict[str, sessionmaker] = {}


def get_system_engine():
    global _system_engine
    if _system_engine is None:
        project_registry.SYSTEM_DB.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{project_registry.SYSTEM_DB.as_posix()}"
        _system_engine = create_engine(
            url, connect_args={"check_same_thread": False}
        )
    return _system_engine


def get_project_engine(project_id: str):
    with _lock:
        if project_id not in _project_engines:
            db_path = project_registry.get_project_db_path(project_id)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{db_path.as_posix()}"
            _project_engines[project_id] = create_engine(
                url, connect_args={"check_same_thread": False}
            )
        return _project_engines[project_id]


def _get_project_session_factory(project_id: str) -> sessionmaker:
    with _lock:
        if project_id not in _project_session_factories:
            engine = get_project_engine(project_id)
            _project_session_factories[project_id] = sessionmaker(
                autocommit=False, autoflush=False, bind=engine
            )
        return _project_session_factories[project_id]


def get_project_id(
    x_project_id: str = Header(None, alias="X-Project-Id"),
    project_id: str = Query(None),
) -> str:
    resolved_id = x_project_id or project_id
    if not resolved_id:
        raise HTTPException(
            status_code=400,
            detail="Project id is required (X-Project-Id header or project_id query param)",
        )
    if not project_registry.get_project(resolved_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return resolved_id


def get_db(
    project_id: str = Depends(get_project_id),
) -> Generator[Session, None, None]:
    SessionLocal = _get_project_session_factory(project_id)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_system_db() -> Generator[Session, None, None]:
    global _system_session_factory
    if _system_session_factory is None:
        _system_session_factory = sessionmaker(
            autocommit=False, autoflush=False, bind=get_system_engine()
        )
    db = _system_session_factory()
    try:
        yield db
    finally:
        db.close()


def init_system_database() -> None:
    from models import models

    engine = get_system_engine()
    models.User.__table__.create(bind=engine, checkfirst=True)


def _ensure_submission_percentage_column(engine) -> None:
    from sqlalchemy import text

    with engine.connect() as conn:
        columns = [
            row[1]
            for row in conn.execute(text("PRAGMA table_info(concentration_entries)"))
        ]
        if "submission_percentage" in columns:
            return

        conn.execute(
            text(
                "ALTER TABLE concentration_entries "
                "ADD COLUMN submission_percentage REAL DEFAULT 100.0"
            )
        )
        conn.execute(
            text(
                """
                UPDATE concentration_entries
                SET submission_percentage = CASE
                    WHEN estimated_quantity > 0
                    THEN (quantity_submitted / estimated_quantity) * 100.0
                    ELSE 100.0
                END
                """
            )
        )
        conn.commit()


def _ensure_drawing_files_column(engine) -> None:
    from sqlalchemy import text

    with engine.connect() as conn:
        columns = [
            row[1]
            for row in conn.execute(text("PRAGMA table_info(concentration_entries)"))
        ]
        if "drawing_files" in columns:
            return

        conn.execute(
            text(
                "ALTER TABLE concentration_entries "
                "ADD COLUMN drawing_files TEXT"
            )
        )
        conn.commit()


def _ensure_calculation_sheet_no_unique(engine) -> None:
    """Migrate calculation_sheets unique key from (sheet_no, drawing_no) to sheet_no only."""
    from sqlalchemy import text

    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='calculation_sheets'"
            )
        ).fetchone()
        if not row or not row[0]:
            return
        table_sql = row[0]
        if "uq_calculation_sheet_drawing" not in table_sql:
            return

        duplicate_groups = conn.execute(
            text(
                """
                SELECT calculation_sheet_no, GROUP_CONCAT(id) AS ids, MAX(id) AS keep_id
                FROM calculation_sheets
                GROUP BY calculation_sheet_no
                HAVING COUNT(*) > 1
                """
            )
        ).fetchall()
        for group in duplicate_groups:
            keep_id = group[2]
            for sheet_id in (int(x) for x in group[1].split(",")):
                if sheet_id == keep_id:
                    continue
                conn.execute(
                    text(
                        "UPDATE calculation_entries "
                        "SET calculation_sheet_id = :keep_id "
                        "WHERE calculation_sheet_id = :sheet_id"
                    ),
                    {"keep_id": keep_id, "sheet_id": sheet_id},
                )
                conn.execute(
                    text("DELETE FROM calculation_sheets WHERE id = :sheet_id"),
                    {"sheet_id": sheet_id},
                )

        conn.execute(
            text(
                """
                CREATE TABLE calculation_sheets_new (
                    id INTEGER NOT NULL PRIMARY KEY,
                    file_name VARCHAR(200) NOT NULL,
                    calculation_sheet_no VARCHAR(100) NOT NULL,
                    drawing_no VARCHAR(100) NOT NULL,
                    description TEXT NOT NULL,
                    comment TEXT,
                    source_file_path VARCHAR(500),
                    import_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME,
                    CONSTRAINT uq_calculation_sheet_no UNIQUE (calculation_sheet_no)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO calculation_sheets_new (
                    id, file_name, calculation_sheet_no, drawing_no, description,
                    comment, source_file_path, import_date, created_at, updated_at
                )
                SELECT
                    id, file_name, calculation_sheet_no, drawing_no, description,
                    comment, source_file_path, import_date, created_at, updated_at
                FROM calculation_sheets
                """
            )
        )
        conn.execute(text("DROP TABLE calculation_sheets"))
        conn.execute(text("ALTER TABLE calculation_sheets_new RENAME TO calculation_sheets"))
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_calculation_sheets_id ON calculation_sheets (id)")
        )
        conn.commit()


def _ensure_submission_breakdown_columns(engine) -> None:
    from sqlalchemy import text

    with engine.connect() as conn:
        for table in ("calculation_entries", "concentration_entries"):
            columns = [
                row[1]
                for row in conn.execute(text(f"PRAGMA table_info({table})"))
            ]
            if "submission_breakdown" not in columns:
                conn.execute(
                    text(
                        f"ALTER TABLE {table} "
                        "ADD COLUMN submission_breakdown TEXT"
                    )
                )
        conn.commit()


def _ensure_calculation_entry_current_invoice_id_column(engine) -> None:
    from sqlalchemy import text

    with engine.connect() as conn:
        columns = [
            row[1]
            for row in conn.execute(text("PRAGMA table_info(calculation_entries)"))
        ]
        if "current_invoice_id" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE calculation_entries "
                    "ADD COLUMN current_invoice_id VARCHAR(100)"
                )
            )
        conn.commit()


def init_project_database(project_id: str) -> None:
    from models import models

    engine = get_project_engine(project_id)
    models.Base.metadata.create_all(bind=engine)
    _ensure_submission_percentage_column(engine)
    _ensure_drawing_files_column(engine)
    _ensure_submission_breakdown_columns(engine)
    _ensure_calculation_entry_current_invoice_id_column(engine)
    _ensure_calculation_sheet_no_unique(engine)


def get_project_upload_dir(project_id: str) -> Path:
    return project_registry.get_project_upload_dir(project_id)


def get_project_export_dir(project_id: str) -> Path:
    return project_registry.get_project_export_dir(project_id)
