"""
Single source of truth for concentration/calculation exports under C:/Fatina.
Used by file_import, pdf_service, excel_service, and bulk export zip layout.
"""
import os
from pathlib import Path
import shutil
import logging

FATINA_BASE_DIR = Path("C:/Fatina")

logger = logging.getLogger(__name__)


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


def fatina_calculation_sheet_dir(section_number: str, calculation_sheet_no: str) -> Path:
    """Item folder sub-directory named after the calculation sheet number."""
    return fatina_section_dir(section_number) / sanitize_folder_name(calculation_sheet_no)


def calculation_file_path(
    section_number: str,
    file_name: str,
    calculation_sheet_no: str | None = None,
) -> Path:
    if calculation_sheet_no:
        return fatina_calculation_sheet_dir(section_number, calculation_sheet_no) / file_name
    return fatina_section_dir(section_number) / file_name


def calculation_file_uri(
    section_number: str,
    file_name: str,
    calculation_sheet_no: str | None = None,
) -> str:
    """Absolute file:// URI for hyperlinks (Excel/PDF) to calculation sheets on disk."""
    return calculation_file_path(
        section_number, file_name, calculation_sheet_no
    ).resolve().as_uri()


def is_upload_copy_path(path: str, upload_root: Path) -> bool:
    """True when path points at a file inside the project uploads directory."""
    try:
        Path(path).resolve().relative_to(upload_root.resolve())
        return True
    except (ValueError, OSError):
        return False


def primary_fatina_source_path(
    filename: str,
    section_numbers: set[str],
    calculation_sheet_no: str | None = None,
) -> str | None:
    """Return the first existing C:/Fatina copy for a calculation sheet file."""
    for section in sorted(section_numbers):
        if calculation_sheet_no:
            nested = calculation_file_path(section, filename, calculation_sheet_no)
            if nested.is_file():
                return str(nested.resolve())
        flat = fatina_section_dir(section) / filename
        if flat.is_file():
            return str(flat.resolve())
    return None


def copy_files_to_calc_sheet_dir(
    section_number: str,
    calculation_sheet_no: str,
    source_paths: list[str],
) -> int:
    """Copy files into C:/Fatina/{section}/{calculation_sheet_no}/."""
    if not section_number or not calculation_sheet_no or not source_paths:
        return 0

    dest_dir = fatina_calculation_sheet_dir(section_number, calculation_sheet_no)
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src_str in source_paths:
        if not src_str:
            continue
        src = Path(src_str)
        if not src.is_file():
            logger.warning(f"Drawing file not found, skipping copy: {src}")
            continue
        dest = dest_dir / src.name
        try:
            shutil.copy2(src, dest)
            copied += 1
            logger.info(f"Copied file to Fatina: {dest}")
        except (PermissionError, OSError) as exc:
            logger.error(f"Failed to copy {src} -> {dest}: {exc}")
    return copied


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
            if sheet.calculation_sheet_no:
                candidates.append(
                    str(
                        calculation_file_path(
                            section,
                            sheet.file_name,
                            sheet.calculation_sheet_no,
                        )
                    )
                )
            candidates.append(str(fatina_section_dir(section) / sheet.file_name))

    for candidate in candidates:
        path = Path(candidate)
        if path.is_file() and not is_upload_copy_path(candidate, upload_root):
            return candidate

    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate

    return sheet.source_file_path
