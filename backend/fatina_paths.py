"""
Single source of truth for concentration/calculation exports under C:/Fatina.
Used by file_import, pdf_service, excel_service, and bulk export zip layout.
"""
import os
from pathlib import Path

FATINA_BASE_DIR = Path("C:/Fatina")


def get_downloads_dir() -> Path:
    """Resolve the current user's Downloads folder (Windows-first)."""
    home = Path.home()
    downloads = home / "Downloads"
    if downloads.is_dir():
        return downloads
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        candidate = Path(userprofile) / "Downloads"
        if candidate.is_dir():
            return candidate
    downloads.mkdir(parents=True, exist_ok=True)
    return downloads


def sanitize_folder_name(folder_name: str) -> str:
    """Sanitize section number for use as a Windows folder name under Fatina."""
    if not folder_name:
        return ""
    return (
        folder_name.replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace("*", "_")
        .replace("?", "_")
        .replace('"', "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("|", "_")
    )


def fatina_section_dir(section_number: str) -> Path:
    return FATINA_BASE_DIR / sanitize_folder_name(section_number)


def calculation_file_uri(section_number: str, file_name: str) -> str:
    """Absolute file:// URI for hyperlinks (Excel/PDF) to calculation sheets on disk."""
    path = (fatina_section_dir(section_number) / file_name).resolve()
    return path.as_uri()


def is_upload_copy_path(path: str, upload_root: Path) -> bool:
    """True when path points at a file inside the project uploads directory."""
    try:
        Path(path).resolve().relative_to(upload_root.resolve())
        return True
    except (ValueError, OSError):
        return False


def primary_fatina_source_path(filename: str, section_numbers: set[str]) -> str | None:
    """Return the first existing C:/Fatina copy for a calculation sheet file."""
    for section in sorted(section_numbers):
        candidate = fatina_section_dir(section) / filename
        if candidate.is_file():
            return str(candidate.resolve())
    return None


def resolve_original_source_path(
    filename: str,
    upload_copy_path: Path,
    source_folder_path: str | None = None,
    relative_path: str | None = None,
) -> str:
    """Prefer the on-disk original over the uploads copy when the source folder is known."""
    if source_folder_path:
        base = Path(source_folder_path)
        if base.is_dir():
            rel = relative_path or filename
            candidate = (base / rel).resolve()
            if candidate.is_file():
                return str(candidate)
            basename = Path(filename).name
            for found in base.rglob(basename):
                if found.is_file():
                    return str(found.resolve())
    return str(upload_copy_path.resolve())


def resolve_calculation_sheet_open_path(sheet, db, upload_root: Path) -> str | None:
    """Return the best on-disk path to open, preferring originals over uploads copies."""
    from models import models

    candidates: list[str] = []
    if sheet.source_file_path:
        candidates.append(sheet.source_file_path)

    if sheet.file_name:
        entries = (
            db.query(models.CalculationEntry)
            .filter(models.CalculationEntry.calculation_sheet_id == sheet.id)
            .all()
        )
        section_numbers = {
            str(entry.section_number).strip()
            for entry in entries
            if entry.section_number
        }
        for section in section_numbers:
            candidates.append(str(fatina_section_dir(section) / sheet.file_name))

    for candidate in candidates:
        path = Path(candidate)
        if path.is_file() and not is_upload_copy_path(candidate, upload_root):
            return candidate

    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate

    return sheet.source_file_path
