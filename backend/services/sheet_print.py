"""Write a PDF copy of each calculation-sheet workbook into its own folder."""

from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle


def pdf_beside_workbook(workbook: Path) -> Path:
    return workbook.with_suffix(".pdf")


def select_columns(frame: pd.DataFrame, columns: Optional[Iterable[int]]) -> pd.DataFrame:
    """columns are 1-based positions. None or empty keeps every column."""
    chosen = [int(col) for col in (columns or []) if int(col) >= 1]
    if not chosen:
        return frame
    indexes = [col - 1 for col in chosen if col - 1 < frame.shape[1]]
    if not indexes:
        return frame.iloc[:, 0:0]
    return frame.iloc[:, indexes]


def write_sheet_pdf(
    workbook: Path,
    destination: Path,
    orientation: str = "landscape",
    margin_mm: float = 10,
    columns: Optional[Iterable[int]] = None,
) -> None:
    frame = pd.read_excel(workbook, header=None)
    frame = select_columns(frame, columns)
    page = landscape(A4) if orientation == "landscape" else A4
    margin = float(margin_mm) * mm
    document = SimpleDocTemplate(
        str(destination),
        pagesize=page,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )
    data = []
    for row in frame.itertuples(index=False):
        data.append(
            [
                "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)[:80]
                for value in row
            ]
        )
    if not data:
        data = [[""]]
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    document.build([table])


def print_workbooks(
    roots: Iterable[Path],
    orientation: str = "landscape",
    margin_mm: float = 10,
    columns: Optional[List[int]] = None,
) -> List[str]:
    written: List[str] = []
    for root in roots:
        if not root.exists():
            continue
        for workbook in root.rglob("*.xlsx"):
            if workbook.name.startswith("~$"):
                continue
            destination = pdf_beside_workbook(workbook)
            write_sheet_pdf(
                workbook,
                destination,
                orientation=orientation,
                margin_mm=margin_mm,
                columns=columns,
            )
            written.append(str(destination))
    return written
