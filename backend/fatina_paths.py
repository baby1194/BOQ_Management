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
