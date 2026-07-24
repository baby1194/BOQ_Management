"""Parse approved signed quantities from Netivei Israel / similar execution PDF reports."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Section / מק"ט values like 02.01.0010 or 51.01.1061
# Exclude date-like values (e.g. 22.12.2025) via year check in is_section_number().
SECTION_RE = re.compile(r"^\d{1,2}(?:\.\d{1,2}){1,}\.\d{3,4}$|^\d{1,2}\.\d{1,2}\.\d{3,4}$")
# Broader pattern: at least two dotted numeric parts
SECTION_LOOSE_RE = re.compile(r"^\d+(?:\.\d+){1,}$")

DEFAULT_SECTION_COLUMN = 'מק"ט'
DEFAULT_QTY_COLUMN = "כמות מצטברת לחשבון נוכחי"


def is_section_number(value: Optional[str]) -> bool:
    if not value:
        return False
    text = str(value).strip()
    if not SECTION_LOOSE_RE.match(text):
        return False
    parts = text.split(".")
    last = parts[-1]
    # Reject calendar years commonly found in report headers
    if len(last) == 4 and last.isdigit():
        year = int(last)
        if 1900 <= year <= 2099 and len(parts) == 3:
            # Likely DD.MM.YYYY
            return False
    return True


# Keep old name as alias for callers/tests
is_makat = is_section_number
MAKAT_RE = SECTION_RE


def _normalize_header(value: Optional[str]) -> str:
    if not value:
        return ""
    # pdfplumber often emits RTL Hebrew reversed; compare both directions
    text = re.sub(r"\s+", "", str(value))
    return text


def _header_matches_name(header: Optional[str], column_name: str) -> bool:
    """True if header matches the user column name (LTR, RTL-reversed, or by tokens)."""
    name = (column_name or "").strip()
    if not name:
        return False
    h = _normalize_header(header)
    if not h:
        return False

    compact = re.sub(r"\s+", "", name)
    if compact in h or compact[::-1] in h:
        return True

    # pdfplumber often reverses each Hebrew word separately, so match all tokens
    tokens = [t for t in re.split(r"\s+", name) if t]
    if len(tokens) <= 1:
        return False
    for token in tokens:
        t = re.sub(r"\s+", "", token)
        if not t:
            continue
        if t not in h and t[::-1] not in h:
            return False
    return True


def _header_matches_makat_default(header: Optional[str]) -> bool:
    text = _normalize_header(header)
    if not text:
        return False
    return 'ט"קמ' in text or 'מק"ט' in text or "מקט" in text or "טקמ" in text


def _header_matches_cumulative_qty_default(header: Optional[str]) -> bool:
    """Match כמות מצטברת לחשבון נוכחי (and its character-reversed form)."""
    text = _normalize_header(header)
    if not text:
        return False
    has_qty = "תומכ" in text or "כמות" in text
    has_cumulative = "תרבטצמ" in text or "מצטברת" in text
    has_current = (
        "יחכונ" in text
        or "נוכחי" in text
        or "ןובשח" in text
        or "חשבון" in text
    )
    is_total = 'כ"הס' in text or 'סה"כ' in text or "סהכ" in text
    return has_qty and has_cumulative and has_current and not is_total


def _parse_quantity(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.split("\n")[-1].strip()
    text = text.replace(",", "").replace(" ", "")
    try:
        return float(text)
    except ValueError:
        return None


def _detect_columns(
    header_row: List[Optional[str]],
    section_column_name: str,
    qty_column_name: str,
) -> Tuple[Optional[int], Optional[int]]:
    section_name = (section_column_name or "").strip()
    qty_name = (qty_column_name or "").strip()
    makat_idx: Optional[int] = None
    qty_idx: Optional[int] = None

    for idx, cell in enumerate(header_row):
        if makat_idx is None:
            if section_name:
                if _header_matches_name(cell, section_name):
                    makat_idx = idx
            elif _header_matches_makat_default(cell):
                makat_idx = idx
        if qty_idx is None:
            if qty_name:
                if _header_matches_name(cell, qty_name):
                    qty_idx = idx
            elif _header_matches_cumulative_qty_default(cell):
                qty_idx = idx
    return makat_idx, qty_idx


def _infer_columns_from_data(
    rows: List[List[Optional[str]]],
) -> Tuple[Optional[int], Optional[int]]:
    """Fallback: find section column from data patterns; qty is typically 5 cols left."""
    for row in rows:
        if not row:
            continue
        for idx, cell in enumerate(row):
            if is_section_number(cell):
                qty_idx = idx - 5 if idx >= 5 else None
                return idx, qty_idx
    return None, None


def _table_has_section_rows(
    rows: List[List[Optional[str]]], section_idx: int, sample_size: int = 5
) -> bool:
    checked = 0
    for row in rows:
        if not row or len(row) <= section_idx:
            continue
        checked += 1
        if is_section_number(row[section_idx]):
            return True
        if checked >= sample_size:
            break
    return False


def build_boq_section_number(structure: str, pdf_section: str) -> str:
    """Combine structure prefix with PDF section number: structure + '.' + section."""
    structure = (structure or "").strip().strip(".")
    pdf_section = (pdf_section or "").strip().lstrip(".")
    if structure and pdf_section:
        return f"{structure}.{pdf_section}"
    return pdf_section


def extract_approved_signed_quantities(
    pdf_path: str | Path,
    section_column_name: str = "",
    qty_column_name: str = "",
) -> Dict[str, float]:
    """
    Extract mapping of PDF section number -> approved signed quantity.

    Column headers are matched against section_column_name / qty_column_name
    (substring, including RTL-reversed text). Empty names fall back to
    built-in מק\"ט / כמות מצטברת לחשבון נוכחי matching.
    """
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError(
            "pdfplumber is required to read approved signed quantity PDFs. "
            "Install it with: pip install pdfplumber"
        ) from exc

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    section_col = (section_column_name or "").strip() or DEFAULT_SECTION_COLUMN
    qty_col = (qty_column_name or "").strip() or DEFAULT_QTY_COLUMN

    results: Dict[str, float] = {}
    known_makat_idx: Optional[int] = None
    known_qty_idx: Optional[int] = None

    with pdfplumber.open(str(path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables() or []
            for table in tables:
                if not table or len(table) < 2:
                    continue

                header = table[0]
                data_rows = table[1:]
                makat_idx, qty_idx = _detect_columns(header, section_col, qty_col)

                if makat_idx is not None and qty_idx is not None:
                    known_makat_idx = makat_idx
                    known_qty_idx = qty_idx
                elif known_makat_idx is not None and known_qty_idx is not None:
                    if _table_has_section_rows(data_rows, known_makat_idx):
                        makat_idx, qty_idx = known_makat_idx, known_qty_idx
                    else:
                        continue
                else:
                    # Only infer from data layout when using default column names
                    if (
                        section_col == DEFAULT_SECTION_COLUMN
                        and qty_col == DEFAULT_QTY_COLUMN
                    ):
                        makat_idx, qty_idx = _infer_columns_from_data(data_rows)
                    else:
                        continue

                if makat_idx is None or qty_idx is None:
                    continue

                for row in data_rows:
                    if not row or len(row) <= max(makat_idx, qty_idx):
                        continue
                    makat_raw = row[makat_idx]
                    if not is_section_number(makat_raw):
                        continue
                    makat = str(makat_raw).strip()
                    quantity = _parse_quantity(row[qty_idx])
                    if quantity is None:
                        logger.debug(
                            "Skipping %s on page %s: unparseable qty %r",
                            makat,
                            page_num,
                            row[qty_idx],
                        )
                        continue
                    results[makat] = quantity

    logger.info(
        "Extracted %s approved signed quantity rows from %s "
        "(section_col=%r, qty_col=%r)",
        len(results),
        path.name,
        section_col,
        qty_col,
    )
    return results
