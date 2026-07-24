"""
Single source of truth for concentration/calculation exports under C:/Fatina.
Used by file_import, pdf_service, excel_service, and bulk export zip layout.
"""
import os
from pathlib import Path
import shutil
import logging
from typing import Dict, List

FATINA_BASE_DIR = Path("C:/Fatina")

logger = logging.getLogger(__name__)


_FINAL_SUBMISSION_IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
}
_FINAL_SUBMISSION_SOURCE_SUFFIXES = {".pdf", *_FINAL_SUBMISSION_IMAGE_SUFFIXES}


def _is_final_submission_pdf(path: Path) -> bool:
    """True for previously produced {section}_final.pdf outputs."""
    name = path.name.lower()
    return name.endswith("_final.pdf")


def _is_final_submission_source(path: Path) -> bool:
    """True for PDF/image inputs that should be merged into the final submission."""
    if not path.is_file():
        return False
    suffix = path.suffix.lower()
    if suffix not in _FINAL_SUBMISSION_SOURCE_SUFFIXES:
        return False
    if suffix == ".pdf" and _is_final_submission_pdf(path):
        return False
    return True


def _append_pdf_pages(writer, pdf_path: Path) -> int:
    """Append all pages from pdf_path into writer as-is (no resize). Returns page count."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    for page in reader.pages:
        writer.add_page(page)
    return len(reader.pages)


def _append_image_as_page(writer, image_path: Path) -> int:
    """Append an image file as a single PDF page sized to the image. Returns 1."""
    from io import BytesIO

    from PIL import Image
    from pypdf import PdfReader
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    with Image.open(image_path) as img:
        # Animated formats (e.g. GIF): use the first frame only.
        try:
            img.seek(0)
        except EOFError:
            pass

        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode == "P":
            img = img.convert("RGBA")
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        width, height = img.size
        image_buf = BytesIO()
        img.save(image_buf, format="PNG")
        image_buf.seek(0)

    pdf_buf = BytesIO()
    canvas = Canvas(pdf_buf, pagesize=(width, height))
    canvas.drawImage(
        ImageReader(image_buf),
        0,
        0,
        width=width,
        height=height,
        preserveAspectRatio=True,
        mask="auto",
    )
    canvas.showPage()
    canvas.save()
    pdf_buf.seek(0)

    reader = PdfReader(pdf_buf)
    writer.add_page(reader.pages[0])
    return 1


def _append_source_file(writer, path: Path) -> int:
    """Append a PDF or image source file; each image becomes one page."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _append_pdf_pages(writer, path)
    if suffix in _FINAL_SUBMISSION_IMAGE_SUFFIXES:
        return _append_image_as_page(writer, path)
    return 0


def produce_final_submission_pdfs(
    base_dir: Path | None = None,
) -> Dict[str, object]:
    """
    For each item folder under Fatina, merge PDFs/images into {section}_final.pdf.

    Order:
      1. Concentration sheet at item root: {section}.pdf
      2. PDF/image files inside each immediate subfolder (calc sheet no / {invoice}_m),
         subfolders sorted by name; files within each folder sorted by name.
         Each image (png/jpg/jpeg/gif/bmp/tif/tiff/webp) is treated as a single-page PDF.

    PDF pages are appended as-is. Existing *_final.pdf files are never used as inputs.
    """
    from pypdf import PdfWriter

    root = Path(base_dir) if base_dir is not None else FATINA_BASE_DIR
    produced: List[str] = []
    skipped: List[str] = []
    errors: List[str] = []

    if not root.is_dir():
        return {
            "produced_count": 0,
            "skipped_count": 0,
            "produced_paths": produced,
            "skipped": skipped,
            "errors": [f"Fatina folder not found: {root}"],
        }

    item_dirs = sorted(
        [p for p in root.iterdir() if p.is_dir()],
        key=lambda p: p.name.lower(),
    )

    for item_dir in item_dirs:
        section = item_dir.name
        output_path = item_dir / f"{section}_final.pdf"
        writer = PdfWriter()
        pages_added = 0
        sources: List[str] = []

        try:
            conc_pdf = item_dir / f"{section}.pdf"
            if conc_pdf.is_file() and not _is_final_submission_pdf(conc_pdf):
                pages_added += _append_pdf_pages(writer, conc_pdf)
                sources.append(str(conc_pdf))

            subdirs = sorted(
                [p for p in item_dir.iterdir() if p.is_dir()],
                key=lambda p: p.name.lower(),
            )
            for subdir in subdirs:
                source_files = sorted(
                    [p for p in subdir.iterdir() if _is_final_submission_source(p)],
                    key=lambda p: p.name.lower(),
                )
                for source_path in source_files:
                    pages_added += _append_source_file(writer, source_path)
                    sources.append(str(source_path))

            if pages_added == 0:
                skipped.append(section)
                logger.info(
                    "Skipping final submission for %s: no PDF/image files found",
                    section,
                )
                continue

            with open(output_path, "wb") as out_f:
                writer.write(out_f)

            produced.append(str(output_path))
            logger.info(
                "Wrote final submission PDF %s (%s pages from %s source(s))",
                output_path,
                pages_added,
                len(sources),
            )
        except Exception as exc:
            msg = f"{section}: {exc}"
            errors.append(msg)
            logger.exception(
                "Failed to produce final submission PDF for %s", section
            )

    return {
        "produced_count": len(produced),
        "skipped_count": len(skipped),
        "produced_paths": produced,
        "skipped": skipped,
        "errors": errors,
    }


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


def fatina_invoice_folder_name(invoice_no: str) -> str:
    """Invoice folder name under an item folder, e.g. invoice 05 -> 05_m."""
    base = sanitize_folder_name(str(invoice_no or "").strip())
    if not base:
        return ""
    return f"{base}_m"


def fatina_invoice_dir(section_number: str, invoice_no: str) -> Path:
    """Item folder sub-directory for drawings when there is no calc sheet number."""
    folder_name = fatina_invoice_folder_name(invoice_no)
    if not folder_name:
        return fatina_section_dir(section_number)
    return fatina_section_dir(section_number) / folder_name


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


def copy_files_to_invoice_dir(
    section_number: str,
    invoice_no: str,
    source_paths: list[str],
) -> int:
    """Copy files into C:/Fatina/{section}/{invoice_no}_m/."""
    if not section_number or not invoice_no or not source_paths:
        return 0

    dest_dir = fatina_invoice_dir(section_number, invoice_no)
    if not fatina_invoice_folder_name(invoice_no):
        return 0

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


def remove_file_from_invoice_dir(
    section_number: str,
    invoice_no: str,
    file_path: str,
) -> bool:
    """Delete a file from C:/Fatina/{section}/{invoice_no}_m/ by basename."""
    if not section_number or not invoice_no or not file_path:
        return False

    filename = Path(file_path).name
    if not filename:
        return False

    dest = fatina_invoice_dir(section_number, invoice_no) / filename
    if not dest.is_file():
        return False

    try:
        dest.unlink()
        logger.info(f"Removed file from Fatina: {dest}")
        return True
    except OSError as exc:
        logger.error(f"Failed to remove {dest}: {exc}")
        return False


def remove_file_from_calc_sheet_dir(
    section_number: str,
    calculation_sheet_no: str,
    file_path: str,
) -> bool:
    """Delete a file from C:/Fatina/{section}/{calculation_sheet_no}/ by basename."""
    if not section_number or not calculation_sheet_no or not file_path:
        return False

    filename = Path(file_path).name
    if not filename:
        return False

    dest = fatina_calculation_sheet_dir(section_number, calculation_sheet_no) / filename
    if not dest.is_file():
        return False

    try:
        dest.unlink()
        logger.info(f"Removed file from Fatina: {dest}")
        return True
    except OSError as exc:
        logger.error(f"Failed to remove {dest}: {exc}")
        return False


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
