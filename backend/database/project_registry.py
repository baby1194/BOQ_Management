import json
import uuid
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

DATABASE_DIR = Path("database")
PROJECTS_DIR = DATABASE_DIR / "projects"
REGISTRY_FILE = DATABASE_DIR / "projects.json"
LEGACY_DB = DATABASE_DIR / "boq_system.db"
SYSTEM_DB = DATABASE_DIR / "system.db"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_project_db_path(project_id: str) -> Path:
    return PROJECTS_DIR / project_id / "boq_system.db"


def get_project_upload_dir(project_id: str) -> Path:
    path = Path("uploads") / project_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_export_dir(project_id: str) -> Path:
    path = Path("exports") / project_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_registry() -> Dict:
    if not REGISTRY_FILE.exists():
        return {"projects": []}
    with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_registry(data: Dict) -> None:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def list_projects() -> List[Dict]:
    return load_registry().get("projects", [])


def get_project(project_id: str) -> Optional[Dict]:
    for project in list_projects():
        if project["id"] == project_id:
            return project
    return None


def create_project_entry(name: str) -> Dict:
    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "name": name.strip(),
        "created_at": _utc_now(),
    }
    data = load_registry()
    data.setdefault("projects", []).append(project)
    save_registry(data)
    return project


def migrate_users_to_system_db(source_db_path: Path) -> None:
    from sqlalchemy.orm import sessionmaker
    from database.database import get_system_engine, get_project_engine
    from models import models

    system_engine = get_system_engine()
    models.User.__table__.create(bind=system_engine, checkfirst=True)

    if not source_db_path.exists():
        return

    source_engine = get_project_engine_from_path(source_db_path)
    SourceSession = sessionmaker(bind=source_engine)
    SystemSession = sessionmaker(bind=system_engine)

    src = SourceSession()
    sys = SystemSession()
    try:
        users = src.query(models.User).all()
        for user in users:
            existing = (
                sys.query(models.User)
                .filter(models.User.username == user.username)
                .first()
            )
            if existing:
                continue
            sys.add(
                models.User(
                    username=user.username,
                    hashed_password=user.hashed_password,
                    system_password=user.system_password,
                    is_active=user.is_active,
                )
            )
        sys.commit()
        if users:
            logger.info("Migrated %d user(s) to system database", len(users))
    except Exception as exc:
        sys.rollback()
        logger.warning("Could not migrate users to system database: %s", exc)
    finally:
        src.close()
        sys.close()


def get_project_engine_from_path(db_path: Path):
    from sqlalchemy import create_engine

    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path.as_posix()}"
    return create_engine(url, connect_args={"check_same_thread": False})


def migrate_legacy_db() -> None:
    """One-time migration: register existing boq_system.db as 'testing project'."""
    if REGISTRY_FILE.exists():
        return

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "name": "testing project",
        "created_at": _utc_now(),
    }

    dest_dir = PROJECTS_DIR / project_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_db = dest_dir / "boq_system.db"

    if LEGACY_DB.exists():
        shutil.move(str(LEGACY_DB), str(dest_db))
        logger.info("Moved legacy database to %s", dest_db)
    else:
        dest_db.touch()
        logger.info("No legacy database found; created empty project database at %s", dest_db)

    save_registry({"projects": [project]})
    migrate_users_to_system_db(dest_db)
