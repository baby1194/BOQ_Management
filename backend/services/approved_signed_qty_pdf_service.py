"""Parse approved signed quantities from Netivei Israel / similar execution PDF reports."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# מק"ט / section numbers like 02.01.0010 or 51.01.1061
# Exclude date-like values (e.g. 22.12.2025) via year check in is_makat().
MAKAT_RE = re.compile(r"^\d{1,2}\.\d{1,2}\.\d{3,4}$")


def is_makat(value: Optional[str]) -> bool:
    if not value:
        return False
    text = str(value).strip()
    if not MAKAT_RE.match(text):
        return False
    last = text.rsplit(".", 1)[-1]
    # Reject calendar years commonly found in report headers
    if len(last) == 4 and last.isdigit():
        year = int(last)
        if 1900 <= year <= 2099:
            return False
    return True


def _normalize_header(value: Optional[str]) -> str:
    if not value:
        return ""
    # pdfplumber often emits RTL Hebrew reversed; compare both directions
    text = re.sub(r"\s+", "", value)
    return text


def _header_matches_makat(header: Optional[str]) -> bool:
    text = _normalize_header(header)
    if not text:
        return False
    # מק"ט appears reversed as ט"קמ
    return 'ט"קמ' in text or 'מק"ט' in text or "מקט" in text or "טקמ" in text


def _header_matches_cumulative_qty(header: Optional[str]) -> bool:
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
    # Exclude total (סה"כ) columns
    is_total = 'כ"הס' in text or 'סה"כ' in text or "סהכ" in text
    return has_qty and has_cumulative and has_current and not is_total


def _parse_quantity(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    # Keep last line when cell has multi-line content
    text = text.split("\n")[-1].strip()
    text = text.replace(",", "").replace(" ", "")
    try:
        return float(text)
    except ValueError:
        return None


def _detect_columns(
    header_row: List[Optional[str]],
) -> Tuple[Optional[int], Optional[int]]:
    makat_idx: Optional[int] = None
    qty_idx: Optional[int] = None
    for idx, cell in enumerate(header_row):
        if makat_idx is None and _header_matches_makat(cell):
            makat_idx = idx
        if qty_idx is None and _header_matches_cumulative_qty(cell):
            qty_idx = idx
    return makat_idx, qty_idx


def _infer_columns_from_data(
    rows: List[List[Optional[str]]],
) -> Tuple[Optional[int], Optional[int]]:
    """Fallback: find MAKAT column from data patterns; qty is typically 5 cols left."""
    for row in rows:
        if not row:
            continue
        for idx, cell in enumerate(row):
            if is_makat(cell):
                qty_idx = idx - 5 if idx >= 5 else None
                return idx, qty_idx
    return None, None


def _table_has_makat_rows(
    rows: List[List[Optional[str]]], makat_idx: int, sample_size: int = 5
) -> bool:
    checked = 0
    for row in rows:
        if not row or len(row) <= makat_idx:
            continue
        checked += 1
        if is_makat(row[makat_idx]):
            return True
        if checked >= sample_size:
            break
    return False


def extract_approved_signed_quantities(pdf_path: str | Path) -> Dict[str, float]:
    """
    Extract mapping of section_number (מק\"ט) -> approved signed quantity
    (כמות מצטברת לחשבון נוכחי) from an approved/signed execution PDF.
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
                makat_idx, qty_idx = _detect_columns(header)

                if makat_idx is not None and qty_idx is not None:
                    known_makat_idx = makat_idx
                    known_qty_idx = qty_idx
                elif known_makat_idx is not None and known_qty_idx is not None:
                    if _table_has_makat_rows(data_rows, known_makat_idx):
                        makat_idx, qty_idx = known_makat_idx, known_qty_idx
                    else:
                        continue
                else:
                    makat_idx, qty_idx = _infer_columns_from_data(data_rows)

                if makat_idx is None or qty_idx is None:
                    continue

                for row in data_rows:
                    if not row or len(row) <= max(makat_idx, qty_idx):
                        continue
                    makat_raw = row[makat_idx]
                    if not is_makat(makat_raw):
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
                    # Later pages can repeat headers; last value wins
                    results[makat] = quantity

    logger.info(
        "Extracted %s approved signed quantity rows from %s",
        len(results),
        path.name,
    )
    return results
