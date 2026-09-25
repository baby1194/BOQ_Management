"""Write a PDF copy of each calculation-sheet workbook into its own folder."""

import os
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

CALCULATION_SHEET_NAME = "Calculation"
_FONT_NAME = "SheetPrintHebrew"


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


def _cell_text(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def drop_empty_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    keep = frame.apply(lambda row: any(_cell_text(value) for value in row), axis=1)
    return frame.loc[keep].reset_index(drop=True)


def read_print_frame(workbook: Path) -> pd.DataFrame:
    """The Calculation sheet when the workbook has one, otherwise the first sheet."""
    book = pd.ExcelFile(workbook)
    sheet = CALCULATION_SHEET_NAME if CALCULATION_SHEET_NAME in book.sheet_names else book.sheet_names[0]
    return pd.read_excel(book, sheet_name=sheet, header=None)


def _ensure_font() -> str:
    if _FONT_NAME in pdfmetrics.getRegisteredFontNames():
        return _FONT_NAME
    for path in (
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\ARIAL.TTF",
        r"C:\Windows\Fonts\tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(_FONT_NAME, path))
            return _FONT_NAME
    return "Helvetica"


def _display_text(value) -> str:
    text = _cell_text(value)
    if any("\u0590" <= char <= "\u05ff" for char in text):
        return get_display(text)
    return text


def write_sheet_pdf(
    workbook: Path,
    destination: Path,
    orientation: str = "landscape",
    margin_mm: float = 10,
    columns: Optional[Iterable[int]] = None,
) -> None:
    frame = drop_empty_rows(select_columns(read_print_frame(workbook), columns))
    page = landscape(A4) if orientation == "landscape" else A4
    margin = max(0.0, float(margin_mm)) * mm
    document = SimpleDocTemplate(
        str(destination),
        pagesize=page,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )
    data = [
        [_display_text(value) for value in row]
        for row in frame.itertuples(index=False)
    ]
    if not data:
        data = [[""]]
    usable = page[0] - (2 * margin)
    column_count = max(len(data[0]), 1)
    column_width = usable / column_count
    font_name = _ensure_font()
    table = Table(data, colWidths=[column_width] * column_count)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
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
