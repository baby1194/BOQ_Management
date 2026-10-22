"""Read a calculation sheet without walking an oversized Excel used range.

Excel often records the used range as the whole grid. Reading that range makes
Track and Check quantities sit on the spinner. This reader keeps rows only
through the last block of detail data.
"""

from __future__ import annotations

import logging
import warnings
from typing import Iterable, List, Sequence, Tuple

logger = logging.getLogger(__name__)

COLUMN_CAP = 600
ROW_CAP = 8000
# Detail lines start at Excel row 28. Stop after this many empty rows in a row.
EMPTY_TAIL = 200
DETAIL_START_EXCEL_ROW = 28


def _is_empty(row: Sequence) -> bool:
    for value in row:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return False
    return True


def bounded_sheet_rows(
    row_iter: Iterable[Sequence],
    *,
    detail_start: int = DETAIL_START_EXCEL_ROW,
    empty_tail: int = EMPTY_TAIL,
    row_cap: int = ROW_CAP,
) -> List[Tuple]:
    """Keep Excel rows from 1, and stop after a run of empty detail rows."""
    rows: List[Tuple] = []
    empty_run = 0
    for index, row in enumerate(row_iter, start=1):
        if index > row_cap:
            logger.warning(
                "Stopped reading a calculation sheet at row %s", row_cap
            )
            break
        values = tuple(row)
        rows.append(values)
        if index < detail_start:
            continue
        if _is_empty(values):
            empty_run += 1
            if empty_run >= empty_tail:
                break
        else:
            empty_run = 0
    return rows


def load_calculation_sheet_rows(path: str) -> List[Tuple]:
    """Rows of the Calculation sheet. Index 0 is Excel row 1."""
    from openpyxl import load_workbook

    from services.excel_service import _patch_openpyxl_custom_filters

    _patch_openpyxl_custom_filters()
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Cannot parse header or footer",
            category=UserWarning,
        )
        workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if "Calculation" not in workbook.sheetnames:
            raise ValueError(f"{path} has no Calculation sheet")
        worksheet = workbook["Calculation"]
        max_column = worksheet.max_column or COLUMN_CAP
        max_column = min(max_column, COLUMN_CAP)
        return bounded_sheet_rows(
            worksheet.iter_rows(max_row=ROW_CAP, max_col=max_column, values_only=True)
        )
    finally:
        workbook.close()
