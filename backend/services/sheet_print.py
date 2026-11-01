"""Write a PDF copy of each calculation-sheet workbook into its own folder."""

import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from bidi.algorithm import get_display
from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries
from openpyxl.worksheet.worksheet import Worksheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Table, TableStyle

CALCULATION_SHEET_NAME = "Calculation"
_FONT_NAME = "SheetPrintHebrew"
_DEFAULT_COLUMN_WIDTH = 8.43
# Area 1 is the title block, repeated on every page. Area 2 is the measurement
# table: every row from row 27 through the last row that has a value in column C.
TITLE_ROW_COUNT = 26
TABLE_START_ROW = 27
TABLE_MARKER_COLUMN = 3


@dataclass
class PrintGrid:
    rows: List[List[str]]
    widths: List[float]
    right_to_left: bool
    spans: List[Tuple[Tuple[int, int], Tuple[int, int]]] = field(default_factory=list)
    numeric: List[Tuple[int, int]] = field(default_factory=list)
    repeat_rows: int = 0
    row_heights: List[float] = field(default_factory=list)
    table_start: Optional[int] = None
    table_columns: List[int] = field(default_factory=list)


def pdf_beside_workbook(workbook: Path) -> Path:
    return workbook.with_suffix(".pdf")


def _has_hebrew(text: str) -> bool:
    return any("\u0590" <= char <= "\u05ff" for char in text)


def format_cell(value) -> str:
    """Show values the way a person reads them: no float noise, dates as day/month/year."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, float):
        rounded = round(value, 3)
        if rounded == int(rounded):
            return str(int(rounded))
        return f"{rounded:.3f}".rstrip("0").rstrip(".")
    return str(value).strip()


def _meaningful(value) -> bool:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(value, 6) != 0
    return format_cell(value) != ""


def calculation_worksheet(workbook) -> Worksheet:
    if CALCULATION_SHEET_NAME in workbook.sheetnames:
        return workbook[CALCULATION_SHEET_NAME]
    return workbook.worksheets[0]


def _print_area_bounds(ws: Worksheet) -> Optional[Tuple[int, int, int, int]]:
    area = ws.print_area
    if not area:
        return None
    first = str(area).split(",")[0]
    ref = first.split("!")[-1].replace("$", "").replace("'", "")
    min_col, min_row, max_col, max_row = range_boundaries(ref)
    return min_row, min_col, max_row, max_col


def _filled_bounds(ws: Worksheet) -> Optional[Tuple[int, int, int, int]]:
    """Print area when one is set, otherwise the smallest block holding every value."""
    area = _print_area_bounds(ws)
    if area:
        return area
    bounds = None
    for row in ws.iter_rows():
        for cell in row:
            if format_cell(cell.value) == "":
                continue
            if bounds is None:
                bounds = [cell.row, cell.column, cell.row, cell.column]
            else:
                bounds[0] = min(bounds[0], cell.row)
                bounds[1] = min(bounds[1], cell.column)
                bounds[2] = max(bounds[2], cell.row)
                bounds[3] = max(bounds[3], cell.column)
    return tuple(bounds) if bounds else None


def _row_height(ws: Worksheet, row: int) -> float:
    """Excel's row height in points. A blank height is Excel's default of 15."""
    dimension = ws.row_dimensions.get(row)
    if dimension is not None and dimension.height:
        return float(dimension.height)
    return 15.0


def _row_hidden(ws: Worksheet, row: int) -> bool:
    dimension = ws.row_dimensions.get(row)
    return bool(dimension is not None and dimension.hidden)


def _hidden_columns(ws: Worksheet) -> set:
    hidden = set()
    for dimension in ws.column_dimensions.values():
        if dimension.hidden and dimension.min and dimension.max:
            hidden.update(range(dimension.min, dimension.max + 1))
    return hidden


def _column_width(ws: Worksheet, column: int) -> float:
    from openpyxl.utils import get_column_letter

    dimension = ws.column_dimensions.get(get_column_letter(column))
    if dimension is not None and dimension.width:
        return float(dimension.width)
    return _DEFAULT_COLUMN_WIDTH


def filled_cell_boxes(
    rows: List[List[str]],
    spans: List[Tuple[Tuple[int, int], Tuple[int, int]]],
    table_start: Optional[int] = None,
    table_columns: Optional[Iterable[int]] = None,
) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """Borders for the two print areas.

    Above the table, a border is drawn around each cell or merged block that
    holds a value. Inside the table, every cell of the table columns is boxed,
    including the empty ones.
    """
    table_at = set(table_columns or [])
    covered = set()
    boxes = []
    for (c0, r0), (c1, r1) in spans:
        cells = [(c, r) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]
        covered.update(cells)
        in_table = table_start is not None and any(
            r >= table_start and c in table_at for c, r in cells
        )
        if in_table or any(rows[r][c] for c, r in cells):
            boxes.append(((c0, r0), (c1, r1)))
    for ri, row in enumerate(rows):
        for ci, text in enumerate(row):
            if (ci, ri) in covered:
                continue
            in_table = table_start is not None and ri >= table_start and ci in table_at
            if text or in_table:
                boxes.append(((ci, ri), (ci, ri)))
    return boxes


def _empty_grid() -> PrintGrid:
    return PrintGrid(rows=[[""]], widths=[1.0], right_to_left=False, row_heights=[15.0])


def _last_table_row(ws: Worksheet, max_row: int) -> Optional[int]:
    """Last row at or below row 27 whose column C has a value."""
    last = None
    upper = max(int(max_row or TABLE_START_ROW), TABLE_START_ROW)
    for row in ws.iter_rows(
        min_row=TABLE_START_ROW,
        max_row=upper,
        min_col=TABLE_MARKER_COLUMN,
        max_col=TABLE_MARKER_COLUMN,
    ):
        if format_cell(row[0].value) != "":
            last = row[0].row
    return last


def _chosen_columns(columns: Optional[Iterable[int]]) -> set:
    return {int(col) for col in (columns or []) if int(col) >= 1}


def build_print_grid(ws: Worksheet, columns: Optional[Iterable[int]] = None) -> PrintGrid:
    """Title block, then the measurement table.

    Rows 1 to 26 keep each cell that has a value. Row 27 through the last row
    with a value in column C is printed in full, empty cells included. A sheet
    with no such table keeps the smaller filled block.
    """
    area = _print_area_bounds(ws)
    covers_marker = area is None or area[1] <= TABLE_MARKER_COLUMN <= area[3]
    scan_end = area[2] if area else (ws.max_row or TABLE_START_ROW)
    last_table = _last_table_row(ws, scan_end) if covers_marker else None
    if last_table and last_table >= TABLE_START_ROW:
        return _table_grid(ws, last_table, columns, area)

    bounds = _filled_bounds(ws)
    if bounds is None:
        return _empty_grid()
    min_row, min_col, max_row, max_col = bounds

    chosen = _chosen_columns(columns)
    hidden = _hidden_columns(ws)
    column_range = [
        c for c in range(min_col, max_col + 1)
        if (not chosen or c in chosen) and c not in hidden
    ]

    header_rows = (
        [r for r in range(1, TITLE_ROW_COUNT + 1) if not _row_hidden(ws, r)]
        if max_row > TITLE_ROW_COUNT
        else []
    )
    body_rows = [
        r for r in range(min_row, max_row + 1)
        if r > TITLE_ROW_COUNT and not _row_hidden(ws, r)
    ]
    if not header_rows:
        body_rows = [r for r in range(min_row, max_row + 1) if not _row_hidden(ws, r)]

    rows_to_read = header_rows + [r for r in body_rows if r not in header_rows]
    values = {
        (r, c): ws.cell(row=r, column=c).value
        for r in rows_to_read
        for c in column_range
    }
    # Formula columns that only hold 0 are part of Excel's used range but not of the sheet.
    kept_cols = [
        c for c in column_range
        if any(_meaningful(values[(r, c)]) for r in rows_to_read)
    ]
    kept_body = [
        r for r in body_rows
        if any(format_cell(values[(r, c)]) for c in kept_cols)
    ]
    kept_rows = header_rows + [r for r in kept_body if r not in header_rows] if header_rows else kept_body
    if not kept_rows or not kept_cols:
        return _empty_grid()
    repeat_rows = len(header_rows) if kept_body else 0
    return _assemble_grid(ws, kept_rows, kept_cols, values, repeat_rows, [])


def _table_grid(ws: Worksheet, last_table: int, columns, area) -> PrintGrid:
    """Rows 1-26 for valued cells, then every table row through column C."""
    chosen = _chosen_columns(columns)
    hidden = _hidden_columns(ws)
    min_col = area[1] if area else 1
    max_col = area[3] if area else (ws.max_column or 1)
    usable = [
        c for c in range(min_col, max_col + 1)
        if c not in hidden and (not chosen or c in chosen)
    ]
    header_rows = [r for r in range(1, TITLE_ROW_COUNT + 1) if not _row_hidden(ws, r)]
    table_rows = [
        r for r in range(TABLE_START_ROW, last_table + 1) if not _row_hidden(ws, r)
    ]
    values = {}
    header_cols = []
    valued_table_cols = []
    for row in ws.iter_rows(
        min_row=1,
        max_row=last_table,
        min_col=min_col,
        max_col=max_col,
    ):
        excel_row = row[0].row
        if excel_row not in header_rows and excel_row not in table_rows:
            continue
        for cell in row:
            if cell.column not in usable:
                continue
            values[(excel_row, cell.column)] = cell.value
            if not _meaningful(cell.value):
                continue
            if excel_row >= TABLE_START_ROW:
                valued_table_cols.append(cell.column)
            else:
                header_cols.append(cell.column)
    if valued_table_cols:
        first, last = min(valued_table_cols), max(valued_table_cols)
        table_cols = [c for c in usable if first <= c <= last]
    else:
        table_cols = []
    kept_cols = sorted(set(header_cols) | set(table_cols))
    kept_rows = header_rows + table_rows
    if not kept_rows or not kept_cols:
        return _empty_grid()
    for row_number in kept_rows:
        for column in kept_cols:
            values.setdefault((row_number, column), None)
    return _assemble_grid(
        ws,
        kept_rows,
        kept_cols,
        values,
        len(header_rows) if table_rows else 0,
        table_cols,
    )


def _assemble_grid(ws, kept_rows, kept_cols, values, repeat_rows, table_excel_cols) -> PrintGrid:
    texts = [[format_cell(values.get((r, c))) for c in kept_cols] for r in kept_rows]
    right_to_left = bool(ws.sheet_view.rightToLeft) or any(
        _has_hebrew(text) for row in texts for text in row
    )

    row_pos = {r: i for i, r in enumerate(kept_rows)}
    col_pos = {c: i for i, c in enumerate(kept_cols)}
    count = len(kept_cols)

    def place(index: int) -> int:
        return count - 1 - index if right_to_left else index

    spans = []
    for merged in ws.merged_cells.ranges:
        rows_in = [row_pos[r] for r in range(merged.min_row, merged.max_row + 1) if r in row_pos]
        cols_in = [col_pos[c] for c in range(merged.min_col, merged.max_col + 1) if c in col_pos]
        if (merged.min_row not in row_pos or merged.min_col not in col_pos
                or (len(rows_in) < 2 and len(cols_in) < 2)):
            continue
        a, b = place(min(cols_in)), place(max(cols_in))
        spans.append(((min(a, b), min(rows_in)), (max(a, b), max(rows_in))))

    numeric = [
        (place(ci), ri)
        for ri, r in enumerate(kept_rows)
        for ci, c in enumerate(kept_cols)
        if isinstance(values[(r, c)], (int, float)) and not isinstance(values[(r, c)], bool)
    ]

    widths = [_column_width(ws, c) for c in kept_cols]
    row_heights = [_row_height(ws, r) for r in kept_rows]
    shown = [[_display(text) for text in row] for row in texts]
    if right_to_left:
        shown = [list(reversed(row)) for row in shown]
        widths = list(reversed(widths))
    for start, end in spans:
        _move_text_to_span_start(shown, start, end)
    table_start = None
    table_columns: List[int] = []
    if table_excel_cols:
        indexed = [i for i, row_number in enumerate(kept_rows) if row_number >= TABLE_START_ROW]
        if indexed:
            table_start = indexed[0]
            table_columns = [place(col_pos[c]) for c in table_excel_cols if c in col_pos]
    return PrintGrid(
        rows=shown,
        widths=widths,
        right_to_left=right_to_left,
        spans=spans,
        numeric=numeric,
        repeat_rows=repeat_rows,
        row_heights=row_heights,
        table_start=table_start,
        table_columns=table_columns,
    )


def _move_text_to_span_start(rows: List[List[str]], start, end) -> None:
    """ReportLab draws a span from its first cell, so the text has to live there."""
    (c0, r0), (c1, r1) = start, end
    if rows[r0][c0]:
        return
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            if rows[r][c]:
                rows[r0][c0], rows[r][c] = rows[r][c], ""
                return


def _heights_that_fit(heights: List[float], repeat_rows: int, frame_height: float) -> List[float]:
    """Keep the repeated title block short enough that one more row still fits on the page."""
    heights = [float(height or 15.0) for height in heights]
    if not heights or frame_height <= 1:
        return heights
    repeat = min(max(repeat_rows, 0), len(heights))
    cushion = 8
    if repeat and repeat < len(heights):
        body = max(heights[repeat:])
        budget = frame_height - body - cushion
        header = sum(heights[:repeat])
        if budget <= 0:
            scale = (frame_height - cushion) / (header + body)
            return [height * scale for height in heights]
        if header > budget:
            scale = budget / header
            heights = [
                height * scale if index < repeat else height
                for index, height in enumerate(heights)
            ]
    elif sum(heights) > frame_height - cushion:
        scale = (frame_height - cushion) / sum(heights)
        heights = [height * scale for height in heights]
    cap = frame_height - cushion
    tallest = max(heights)
    if tallest > cap > 0:
        scale = cap / tallest
        heights = [height * scale for height in heights]
    return heights


def wrap_cells(
    grid: PrintGrid,
    col_widths: List[float],
    font_name: str,
    font_size: float,
    padding: float,
    max_height: float = 400,
) -> List[Tuple[Tuple[int, int], float]]:
    """Wrap text inside its own cell, and make the row tall enough to show every line.

    A number, or a single word wider than the cell, is shrunk instead of split.
    A wrapped block is also shrunk when it would be taller than the page.
    """
    merged_width = {}
    covered = set()
    for (c0, r0), (c1, r1) in grid.spans:
        covered.update((c, r) for c in range(c0, c1 + 1) for r in range(r0, r1 + 1))
        merged_width[(c0, r0)] = sum(col_widths[c0:c1 + 1])
    numeric = set(grid.numeric)
    sizes = []
    leading = font_size * 1.2
    for ri, row in enumerate(grid.rows):
        needed = grid.row_heights[ri] if ri < len(grid.row_heights) else 15.0
        for ci, text in enumerate(row):
            if not text or (ci, ri) in covered and (ci, ri) not in merged_width:
                continue
            have = merged_width.get((ci, ri), col_widths[ci] if ci < len(col_widths) else 1.0)
            room = max(have - 2 * padding, 1.0)
            if (ci, ri) in numeric:
                need = pdfmetrics.stringWidth(text, font_name, font_size)
                if need > room:
                    sizes.append(((ci, ri), max(4.0, font_size * room / need)))
                continue
            size = font_size
            lines = simpleSplit(text, font_name, size, room) or [text]
            while len(lines) * (size * 1.2) + 4 > max_height and size > 4:
                size = max(4.0, size * max_height / (len(lines) * (size * 1.2) + 4))
                lines = simpleSplit(text, font_name, size, room) or [text]
            if len(lines) == 1 and pdfmetrics.stringWidth(lines[0], font_name, size) > room:
                need = pdfmetrics.stringWidth(lines[0], font_name, size)
                sizes.append(((ci, ri), max(4.0, size * room / need)))
                continue
            if size < font_size - 0.05:
                sizes.append(((ci, ri), size))
            if _has_hebrew(text) and len(lines) > 1:
                # The text is already in visual order, so its last words come first.
                lines = list(reversed(lines))
            if len(lines) > 1:
                grid.rows[ri][ci] = "\n".join(lines)
            needed = max(needed, len(lines) * (size * 1.2) + 4)
        if ri < len(grid.row_heights):
            grid.row_heights[ri] = needed
        else:
            grid.row_heights.append(needed)
    return sizes


def _display(text: str) -> str:
    return get_display(text) if _has_hebrew(text) else text


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


def write_sheet_pdf(
    workbook: Path,
    destination: Path,
    orientation: str = "landscape",
    margin_mm: float = 10,
    columns: Optional[Iterable[int]] = None,
) -> None:
    book = load_workbook(workbook, data_only=True)
    try:
        grid = build_print_grid(calculation_worksheet(book), columns)
    finally:
        book.close()

    page = landscape(A4) if orientation == "landscape" else A4
    margin = max(0.0, float(margin_mm)) * mm
    document = BaseDocTemplate(str(destination), pagesize=page)
    frame = Frame(
        margin,
        margin,
        page[0] - 2 * margin,
        page[1] - 2 * margin,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    document.addPageTemplates([PageTemplate(frames=[frame])])
    usable = page[0] - (2 * margin)
    total = sum(grid.widths) or 1.0
    col_widths = [usable * width / total for width in grid.widths]
    font_name = _ensure_font()
    font_size = 8.0
    padding = 2
    frame_height = page[1] - (2 * margin)
    sizes = wrap_cells(
        grid, col_widths, font_name, font_size, padding, max_height=frame_height * 0.45
    )
    before = [float(height or 15.0) for height in (grid.row_heights or [15.0] * len(grid.rows))]
    heights = _heights_that_fit(before, grid.repeat_rows, frame_height)
    row_scale = [
        (new / old) if old > 1 and new < old - 0.05 else 1.0
        for old, new in zip(before, heights)
    ]
    sizes = [
        (cell, size * row_scale[cell[1]] if cell[1] < len(row_scale) else size)
        for cell, size in sizes
    ]
    align = "RIGHT" if grid.right_to_left else "LEFT"
    style = [
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size * 1.2),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), align),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]
    for row_index, factor in enumerate(row_scale):
        if factor < 0.999:
            style.append(("FONTSIZE", (0, row_index), (-1, row_index), font_size * factor))
            style.append(("LEADING", (0, row_index), (-1, row_index), font_size * factor * 1.2))
    style += [("SPAN", start, end) for start, end in grid.spans]
    style += [
        ("BOX", start, end, 0.25, colors.grey)
        for start, end in filled_cell_boxes(
            grid.rows, grid.spans, grid.table_start, grid.table_columns
        )
    ]
    style += [("ALIGN", cell, cell, "CENTER") for cell in grid.numeric]
    style += [("FONTSIZE", cell, cell, size) for cell, size in sizes]
    style += [("LEADING", cell, cell, size * 1.2) for cell, size in sizes]
    table = Table(
        grid.rows,
        colWidths=col_widths,
        rowHeights=heights,
        repeatRows=grid.repeat_rows,
        hAlign="RIGHT" if grid.right_to_left else "LEFT",
    )
    table.setStyle(TableStyle(style))
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
