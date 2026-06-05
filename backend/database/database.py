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


def init_project_database(project_id: str) -> None:
    from models import models

    engine = get_project_engine(project_id)
    models.Base.metadata.create_all(bind=engine)


def get_project_upload_dir(project_id: str) -> Path:
    return project_registry.get_project_upload_dir(project_id)


def get_project_export_dir(project_id: str) -> Path:
    return project_registry.get_project_export_dir(project_id)
