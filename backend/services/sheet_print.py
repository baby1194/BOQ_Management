"""Write a PDF copy of each calculation-sheet workbook into its own folder."""

import io
import logging
import os
import re
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from xml.etree import ElementTree as ET

from bidi.algorithm import get_display
from openpyxl.utils.cell import range_boundaries
from openpyxl.worksheet.worksheet import Worksheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Table,
    TableStyle,
)

CALCULATION_SHEET_NAME = "Calculation"
_FONT_NAME = "SheetPrintHebrew"
_DEFAULT_COLUMN_WIDTH = 8.43
_MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_OFFICE_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
logger = logging.getLogger(__name__)
# Rows 1-27 repeat on every page. Row 27 is the measurement column titles.
# The lines below run through the last value in column C when that column is
# filled, and otherwise through the last row that has any value.
TITLE_ROW_COUNT = 26
TABLE_START_ROW = 27
REPEAT_THROUGH_ROW = 27
TABLE_MARKER_COLUMN = 3


@dataclass
class PrintGrid:
    rows: List[List[str]]
    widths: List[float]
    right_to_left: bool
    spans: List[Tuple[Tuple[int, int], Tuple[int, int]]] = field(default_factory=list)
    numeric: List[Tuple[int, int]] = field(default_factory=list)
    centered: List[Tuple[int, int]] = field(default_factory=list)
    repeat_rows: int = 0
    row_heights: List[float] = field(default_factory=list)
    table_start: Optional[int] = None
    table_columns: List[int] = field(default_factory=list)


def pdf_beside_workbook(workbook: Path) -> Path:
    return workbook.with_suffix(".pdf")


@dataclass
class PrintBatch:
    files: List[str]
    errors: List[str]


def _sheet_parts(path: Path, sheet_name: str) -> Tuple[bytes, Optional[str], str]:
    """Sheet XML, the print area for that sheet, and the dimension ref."""
    with zipfile.ZipFile(path) as book:
        workbook_xml = book.read("xl/workbook.xml")
        root = ET.fromstring(workbook_xml)
        sheets_element = root.find(f"{_MAIN_NS}sheets")
        sheets = list(sheets_element) if sheets_element is not None else []
        relation_id = None
        sheet_index = None
        for index, sheet in enumerate(sheets):
            if sheet.attrib.get("name") == sheet_name:
                relation_id = sheet.attrib.get(f"{_OFFICE_REL_NS}id")
                sheet_index = index
                break
        if relation_id is None:
            raise ValueError(f"{path} has no sheet named {sheet_name}")
        rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        target = None
        for rel in rels.findall(f"{_PKG_REL_NS}Relationship"):
            if rel.attrib.get("Id") == relation_id:
                target = rel.attrib["Target"].lstrip("/")
                break
        if not target:
            raise ValueError(f"{path} is missing the worksheet for {sheet_name}")
        if not target.startswith("xl/"):
            target = "xl/" + target
        xml = book.read(target)
    print_area = None
    for name in root.findall(f"{_MAIN_NS}definedNames/{_MAIN_NS}definedName"):
        if name.attrib.get("name") != "_xlnm.Print_Area":
            continue
        local_sheet = name.attrib.get("localSheetId")
        if local_sheet is not None and sheet_index is not None and int(local_sheet) != sheet_index:
            continue
        if name.text:
            print_area = name.text
            break
    dimension = ""
    match = re.search(br'<dimension[^>]*ref="([^"]+)"', xml[:20000])
    if match:
        dimension = match.group(1).decode("ascii", errors="replace")
    return xml, print_area, dimension


def _print_meta(xml: bytes, kept_rows: int, kept_cols: int) -> dict:
    """Column widths, row heights, and merges, without reading phantom rows."""
    meta = {
        "rtl": False,
        "default_row_height": 15.0,
        "col_widths": {},
        "hidden_cols": set(),
        "row_heights": {},
        "hidden_rows": set(),
        "merges": [],
    }
    for _, element in ET.iterparse(io.BytesIO(xml), events=("end",)):
        tag = element.tag
        if tag == f"{_MAIN_NS}sheetView":
            if element.attrib.get("rightToLeft") == "1":
                meta["rtl"] = True
        elif tag == f"{_MAIN_NS}sheetFormatPr":
            height = element.attrib.get("defaultRowHeight")
            if height:
                meta["default_row_height"] = float(height)
        elif tag == f"{_MAIN_NS}col":
            first = int(element.attrib.get("min", 1))
            last = min(int(element.attrib.get("max", first)), kept_cols)
            if first <= kept_cols:
                hidden = element.attrib.get("hidden") in ("1", "true")
                width = element.attrib.get("width")
                for column in range(first, last + 1):
                    if width:
                        meta["col_widths"][column] = float(width)
                    if hidden:
                        meta["hidden_cols"].add(column)
        elif tag == f"{_MAIN_NS}row":
            row_number = int(element.attrib.get("r") or 0)
            if row_number > kept_rows:
                break
            if element.attrib.get("hidden") in ("1", "true"):
                meta["hidden_rows"].add(row_number)
            height = element.attrib.get("ht")
            if height:
                meta["row_heights"][row_number] = float(height)
            element.clear()
    merge_at = xml.rfind(b"<mergeCells")
    if merge_at >= 0:
        merge_end = xml.find(b"</mergeCells>", merge_at)
        chunk = xml[merge_at:merge_end if merge_end >= 0 else merge_at + 20000]
        meta["merges"] = [
            ref.decode("ascii")
            for ref in re.findall(br'ref="([A-Z]+\d+:[A-Z]+\d+)"', chunk)
        ]
    return meta


def load_print_workbook(path: Path):
    """A workbook holding only the rows that actually contain the calculation.

    Excel sometimes records the used range as the whole grid, including a
    million empty rows. Loading that range locks the server.
    """
    from openpyxl import Workbook, load_workbook
    from openpyxl.utils import get_column_letter

    from services.excel_service import (
        _patch_openpyxl_custom_filters,
        _patch_openpyxl_header_footer,
        _patch_openpyxl_pattern_fill,
    )
    from utils.calc_sheet_reader import COLUMN_CAP, ROW_CAP, bounded_sheet_rows

    _patch_openpyxl_custom_filters()
    _patch_openpyxl_pattern_fill()
    _patch_openpyxl_header_footer()
    source = load_workbook(path, read_only=True, data_only=True)
    try:
        if CALCULATION_SHEET_NAME in source.sheetnames:
            worksheet = source[CALCULATION_SHEET_NAME]
        elif source.worksheets:
            worksheet = source.worksheets[0]
        else:
            raise ValueError(f"{path} has no worksheets")
        sheet_name = worksheet.title
        max_column = min(int(worksheet.max_column or COLUMN_CAP), COLUMN_CAP)
        rows = bounded_sheet_rows(
            worksheet.iter_rows(
                max_row=ROW_CAP,
                max_col=max_column,
                values_only=True,
            )
        )
    finally:
        source.close()

    kept_rows = len(rows)
    kept_cols = max((len(row) for row in rows), default=1)
    try:
        sheet_xml, print_area, dimension = _sheet_parts(path, sheet_name)
        meta = _print_meta(sheet_xml, max(kept_rows, 1), max(kept_cols, 1))
    except Exception:
        logger.exception("Could not read the print layout of %s", path)
        print_area = None
        dimension = ""
        meta = _print_meta(b"<worksheet/>", 1, 1)
    if dimension and re.search(r"\d{5,}", dimension):
        logger.warning(
            "%s records used range %s; printing the first %s rows only",
            path.name,
            dimension,
            kept_rows,
        )

    book = Workbook()
    sheet = book.active
    sheet.title = sheet_name[:31]
    for row_number, row in enumerate(rows, start=1):
        for column, value in enumerate(row, start=1):
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            sheet.cell(row=row_number, column=column, value=value)
    for column, width in meta["col_widths"].items():
        letter = get_column_letter(column)
        dimension_cell = sheet.column_dimensions[letter]
        dimension_cell.width = width
        dimension_cell.min = column
        dimension_cell.max = column
    for column in meta["hidden_cols"]:
        letter = get_column_letter(column)
        dimension_cell = sheet.column_dimensions[letter]
        dimension_cell.hidden = True
        dimension_cell.min = column
        dimension_cell.max = column
    for row_number in range(1, kept_rows + 1):
        height = meta["row_heights"].get(row_number, meta["default_row_height"])
        sheet.row_dimensions[row_number].height = height
        if row_number in meta["hidden_rows"]:
            sheet.row_dimensions[row_number].hidden = True
    for ref in meta["merges"]:
        min_col, min_row, max_col, max_row = range_boundaries(ref)
        if min_row > kept_rows or min_col > kept_cols:
            continue
        max_row = min(max_row, kept_rows)
        max_col = min(max_col, kept_cols)
        if min_row == max_row and min_col == max_col:
            continue
        sheet.merge_cells(
            start_row=min_row,
            start_column=min_col,
            end_row=max_row,
            end_column=max_col,
        )
    sheet.sheet_view.rightToLeft = bool(meta["rtl"])
    if print_area and kept_rows and kept_cols:
        plain = print_area.split(",")[0].split("!")[-1].replace("$", "").replace("'", "")
        try:
            min_col, min_row, max_col, max_row = range_boundaries(plain)
        except ValueError:
            min_col = min_row = max_col = max_row = None
        if min_col is not None:
            max_row = min(max_row, kept_rows)
            max_col = min(max_col, kept_cols)
            if min_row <= max_row and min_col <= max_col:
                sheet.print_area = (
                    f"{get_column_letter(min_col)}{min_row}:{get_column_letter(max_col)}{max_row}"
                )
    info = {
        "sheet": sheet_name,
        "rows": kept_rows,
        "cols": kept_cols,
        "dimension": dimension,
    }
    return book, info


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


def excel_width_to_points(width: float) -> float:
    """Excel's character width as printed points, at the usual 96 dpi."""
    width = float(width or _DEFAULT_COLUMN_WIDTH)
    if width <= 0:
        width = _DEFAULT_COLUMN_WIDTH
    pixels = width * 12 if width < 1 else width * 7 + 5
    return pixels * 72 / 96


def fitted_column_widths(excel_widths: List[float], usable: float) -> List[float]:
    """Keep each column at its Excel width, and shrink the row only to fit the page.

    Stretching a short sheet out to the full page leaves the values floating in
    wide empty cells.
    """
    points = [excel_width_to_points(width) for width in excel_widths] or [usable]
    total = sum(points) or 1.0
    if usable > 1 and total > usable:
        scale = usable / total
        points = [width * scale for width in points]
    return points


def _unbreakable(text: str) -> bool:
    """A number or a code stays on one line. A sentence may wrap."""
    compact = " ".join(str(text).split())
    return bool(compact) and " " not in compact


def content_column_widths(
    grid: PrintGrid,
    font_name: str,
    font_size: float,
    padding: float,
    usable: float,
) -> List[float]:
    """Size each column to its text, and wrap a long sentence instead of widening the page."""
    count = len(grid.rows[0]) if grid.rows else 0
    if count <= 0:
        return [usable]
    empty = 8.0
    cap = 90.0
    pad = padding * 2 + 6
    widths = [empty] * count
    origin = {}
    covered = set()
    for (c0, r0), (c1, r1) in grid.spans:
        origin[(c0, r0)] = (c0, min(c1, count - 1))
        for column in range(c0, min(c1, count - 1) + 1):
            for row_index in range(r0, r1 + 1):
                covered.add((column, row_index))
    span_needs = []
    for row_index, row in enumerate(grid.rows):
        for column, text in enumerate(row):
            if not text or column >= count:
                continue
            if (column, row_index) in covered and (column, row_index) not in origin:
                continue
            widest = max(
                pdfmetrics.stringWidth(line, font_name, font_size)
                for line in str(text).split("\n")
            )
            need = widest + pad
            if not _unbreakable(text):
                need = min(need, cap)
            if (column, row_index) in origin:
                span_needs.append((origin[(column, row_index)][0], origin[(column, row_index)][1], need))
            else:
                widths[column] = max(widths[column], need)
    for start, end, need in span_needs:
        have = sum(widths[start:end + 1])
        if have >= need:
            continue
        share = (need - have) / (end - start + 1)
        for column in range(start, end + 1):
            widths[column] += share
    total = sum(widths) or 1.0
    if usable > 1 and total > usable:
        scale = usable / total
        widths = [width * scale for width in widths]
    return widths


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


def border_commands(grid: PrintGrid):
    """Border commands for the PDF table.

    A box on every measurement cell makes ReportLab rebuild those lines on
    every page split, which stalls the server on a long sheet. The measurement
    block is one grid. Cells above it still get a box only when they have a value.
    """
    boxes = filled_cell_boxes(
        grid.rows, grid.spans, grid.table_start, grid.table_columns
    )
    commands = []
    if grid.table_start is not None and grid.table_columns:
        left = min(grid.table_columns)
        right = max(grid.table_columns)
        bottom = len(grid.rows) - 1
        if bottom >= grid.table_start and right >= left:
            commands.append(
                ("GRID", (left, grid.table_start), (right, bottom), 0.25, colors.grey)
            )
        boxes = [box for box in boxes if box[1][1] < grid.table_start]
    commands.extend(("BOX", start, end, 0.25, colors.grey) for start, end in boxes)
    return commands


def _empty_grid() -> PrintGrid:
    return PrintGrid(rows=[[""]], widths=[1.0], right_to_left=False, row_heights=[15.0])


def _last_table_row(ws: Worksheet, max_row: int, min_col: int, max_col: int) -> Optional[int]:
    """Last measurement row.

    Column C marks the end of the table when the lines under row 27 use it.
    A sheet whose lines leave column C empty runs through the last row that
    has a value anywhere in the printed columns.
    """
    last_marker = None
    last_any = None
    upper = max(int(max_row or TABLE_START_ROW), TABLE_START_ROW)
    upper = min(upper, int(ws.max_row or upper))
    last_col = max(int(max_col or min_col), min_col)
    for row in ws.iter_rows(
        min_row=TABLE_START_ROW,
        max_row=upper,
        min_col=min_col,
        max_col=last_col,
    ):
        saw_value = False
        saw_marker = False
        for cell in row:
            if format_cell(cell.value) == "":
                continue
            saw_value = True
            if cell.column == TABLE_MARKER_COLUMN:
                saw_marker = True
        if saw_value:
            last_any = row[0].row
        if saw_marker:
            last_marker = row[0].row
    if last_marker and last_marker > TABLE_START_ROW:
        return last_marker
    return last_any


def _chosen_columns(columns: Optional[Iterable[int]]) -> set:
    return {int(col) for col in (columns or []) if int(col) >= 1}


def build_print_grid(ws: Worksheet, columns: Optional[Iterable[int]] = None) -> PrintGrid:
    """Title block, then the measurement table.

    Rows 1 to 26 keep each cell that has a value. Row 27 through the last
    measurement row is printed in full, empty cells included. A sheet with no
    such table keeps the smaller filled block.
    """
    area = _print_area_bounds(ws)
    min_col = area[1] if area else 1
    max_col = area[3] if area else (ws.max_column or 1)
    scan_end = area[2] if area else (ws.max_row or TABLE_START_ROW)
    last_table = _last_table_row(ws, scan_end, min_col, max_col)
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
        sum(1 for row in kept_rows if row <= REPEAT_THROUGH_ROW) if table_rows else 0,
        table_cols,
    )


_ITEM_NUMBER_KEYS = {
    "מססעיף",
    "מספרסעיף",
    "מספריט",
    "מספרפריט",
    "itemno",
    "itemnumber",
    "sectionno",
    "sectionnumber",
}


def _row_centers_item_or_description(cells: List[str]) -> bool:
    """A title row that holds the item number or the item description."""
    for text in cells:
        if not text:
            continue
        if "תיאור" in text or "תאור" in text:
            return True
        key = re.sub(r"[\s'\"`׳״]", "", text).lower()
        if "description" in key or key in _ITEM_NUMBER_KEYS:
            return True
    return False


def _is_item_number(text: str) -> bool:
    """A BOQ item number such as 1.51.02.0030."""
    return bool(re.fullmatch(r"\d+(?:\.\d+){2,}", text.strip()))


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
    center_rows = {
        ri
        for ri, excel_row in enumerate(kept_rows)
        if excel_row < TABLE_START_ROW and _row_centers_item_or_description(texts[ri])
    }
    # The item card stacks the code, the description and the item number in one
    # column. Centering only the labelled row leaves the other lines on the side.
    item_columns = {
        place(column)
        for row_index, excel_row in enumerate(kept_rows)
        if excel_row < TABLE_START_ROW
        for column, text in enumerate(texts[row_index])
        if _is_item_number(text)
    }
    shown = [[_display(text) for text in row] for row in texts]
    if right_to_left:
        shown = [list(reversed(row)) for row in shown]
        widths = list(reversed(widths))
    for start, end in spans:
        _move_text_to_span_start(shown, start, end)
    centered = []
    for row_index, excel_row in enumerate(kept_rows):
        if row_index >= len(shown) or excel_row > TABLE_START_ROW:
            continue
        for column, text in enumerate(shown[row_index]):
            if not text:
                continue
            # Row 27 is the measurement column titles. The lines under it stay as they are.
            if excel_row == TABLE_START_ROW or row_index in center_rows or column in item_columns:
                centered.append((column, row_index))
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
        centered=centered,
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
    """Shrink a repeated title so several measurement rows fit under it.

    Leaving only one measurement row turns a long sheet into hundreds of pages
    and the PDF build stalls.
    """
    heights = [float(height or 15.0) for height in heights]
    if not heights or frame_height <= 1:
        return heights
    repeat = min(max(repeat_rows, 0), len(heights))
    cushion = 8
    if repeat and repeat < len(heights):
        body = max(heights[repeat:]) or 15.0
        header_cap = min(frame_height * 0.42, frame_height - body - cushion)
        header = sum(heights[:repeat])
        if header_cap <= 1:
            scale = (frame_height - cushion) / (header + body)
            return [height * scale for height in heights]
        if header > header_cap:
            scale = header_cap / header
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


def measurement_content_height(row: List[str], line_height: float) -> float:
    """One line when the text fits, taller when a cell has wrapped onto more lines."""
    lines = 1
    for text in row:
        if text:
            lines = max(lines, str(text).count("\n") + 1)
    if lines <= 1:
        return float(line_height)
    leading = max(float(line_height) - 2, 1.0)
    return lines * leading + 2


def fit_print_row_heights(
    heights: List[float],
    repeat_rows: int,
    frame_height: float,
    line_height: float,
    rows: Optional[List[List[str]]] = None,
) -> List[float]:
    """Keep the column-title row. Measurement rows stay one line unless text wraps."""
    heights = [float(height or 15.0) for height in heights]
    repeat = min(max(repeat_rows, 0), len(heights))
    if repeat and repeat < len(heights):
        heights = [
            height
            if index < repeat
            else measurement_content_height(
                rows[index] if rows and index < len(rows) else [],
                line_height,
            )
            for index, height in enumerate(heights)
        ]
    return _heights_that_fit(heights, repeat_rows, frame_height)


def measurement_font_size(grid: PrintGrid, cell_sizes, row_scales: List[float], font_size: float) -> float:
    """The font rows 1-27 are actually drawn at, so the lines below can match it.

    Title text is often shrunk again to fit a narrow cell. Matching only the
    row-height scale leaves the measurement numbers larger than that text.
    """
    repeat = min(grid.repeat_rows, len(row_scales), len(grid.rows))
    if repeat <= 0:
        return font_size
    by_cell = {cell: size for cell, size in cell_sizes}
    used = []
    for row_index in range(repeat):
        factor = row_scales[row_index]
        for column, text in enumerate(grid.rows[row_index]):
            if not text:
                continue
            used.append(by_cell.get((column, row_index), font_size) * factor)
    if not used:
        return font_size
    used.sort()
    return used[len(used) // 2]


def _title_font_scale(before: List[float], heights: List[float], repeat_rows: int) -> float:
    """Scale used to shrink the repeated title, so the lines below can match it."""
    repeat = min(max(repeat_rows, 0), len(before), len(heights))
    factors = [
        heights[index] / before[index]
        for index in range(repeat)
        if before[index] > 1 and heights[index] < before[index] - 0.05
    ]
    if not factors:
        return 1.0
    return sum(factors) / len(factors)


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


def cell_alignment(grid: PrintGrid) -> str:
    """Center every word, the same way as the item number and the description."""
    return "CENTER"


def _zip_target(base: str, target: str) -> str:
    """Resolve a workbook relationship target against the file that owns it."""
    if target.startswith("/"):
        return target.lstrip("/")
    parent = base.rsplit("/", 1)[0] if "/" in base else ""
    parts: List[str] = []
    for piece in f"{parent}/{target}".split("/"):
        if piece == "..":
            if parts:
                parts.pop()
        elif piece and piece != ".":
            parts.append(piece)
    return "/".join(parts)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def sheet_pictures(path: Path, sheet_name: str) -> List[bytes]:
    """Pictures on the calculation sheet, from the top of the sheet downward.

    A screenshot pasted into the workbook is stored beside the cells. The PDF
    prints the grid first and then these pictures, one after another.
    """
    book = None
    try:
        book = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile):
        return []
    names = set(book.namelist())
    try:
        workbook_xml = ET.fromstring(book.read("xl/workbook.xml"))
        sheets = workbook_xml.find(f"{_MAIN_NS}sheets")
        relation_id = None
        for sheet in list(sheets) if sheets is not None else []:
            if sheet.attrib.get("name") == sheet_name:
                relation_id = sheet.attrib.get(f"{_OFFICE_REL_NS}id")
                break
        if not relation_id or "xl/_rels/workbook.xml.rels" not in names:
            return []
        rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        sheet_target = None
        for rel in rels.findall(f"{_PKG_REL_NS}Relationship"):
            if rel.attrib.get("Id") == relation_id:
                sheet_target = rel.attrib.get("Target") or ""
                break
        if not sheet_target:
            return []
        sheet_path = _zip_target("xl/workbook.xml", sheet_target)
        rels_path = sheet_path.rsplit("/", 1)[0] + "/_rels/" + sheet_path.rsplit("/", 1)[-1] + ".rels"
        if rels_path not in names:
            return []
        drawing_paths = []
        for rel in ET.fromstring(book.read(rels_path)).findall(f"{_PKG_REL_NS}Relationship"):
            kind = rel.attrib.get("Type") or ""
            if not kind.endswith("/drawing"):
                continue
            drawing_paths.append(_zip_target(sheet_path, rel.attrib.get("Target") or ""))
        pictures = []
        for drawing_path in drawing_paths:
            if drawing_path not in names:
                continue
            drawing_rels = drawing_path.rsplit("/", 1)[0] + "/_rels/" + drawing_path.rsplit("/", 1)[-1] + ".rels"
            media = {}
            if drawing_rels in names:
                for rel in ET.fromstring(book.read(drawing_rels)).findall(f"{_PKG_REL_NS}Relationship"):
                    media[rel.attrib.get("Id")] = _zip_target(
                        drawing_path, rel.attrib.get("Target") or ""
                    )
            root = ET.fromstring(book.read(drawing_path))
            for anchor in root.iter():
                if _local_name(anchor.tag) not in ("twoCellAnchor", "oneCellAnchor", "absoluteAnchor"):
                    continue
                row_number = 10**9
                column_number = 0
                for child in anchor:
                    if _local_name(child.tag) != "from":
                        continue
                    for part in child:
                        name = _local_name(part.tag)
                        if name == "row" and part.text and part.text.isdigit():
                            row_number = int(part.text)
                        elif name == "col" and part.text and part.text.isdigit():
                            column_number = int(part.text)
                embed = None
                for node in anchor.iter():
                    if _local_name(node.tag) != "blip":
                        continue
                    for key, value in node.attrib.items():
                        if key == "embed" or key.endswith("}embed"):
                            embed = value
                            break
                if not embed or embed not in media or media[embed] not in names:
                    continue
                pictures.append((row_number, column_number, len(pictures), media[embed]))
        pictures.sort()
        return [book.read(item[3]) for item in pictures]
    except (KeyError, ET.ParseError, OSError):
        logger.exception("Could not read pictures from %s", path)
        return []
    finally:
        book.close()


def _picture_flowable(blob: bytes, max_width: float, max_height: float):
    """One picture fitted on a page, keeping its shape."""
    stream = io.BytesIO(blob)
    try:
        width, height = ImageReader(stream).getSize()
    except Exception:
        logger.warning("Skipped a calculation-sheet picture that could not be read")
        return None
    if width <= 0 or height <= 0:
        return None
    scale = min(max_width / float(width), max_height / float(height))
    stream.seek(0)
    picture = Image(stream, width=width * scale, height=height * scale)
    picture.hAlign = "CENTER"
    return picture


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
    started = time.perf_counter()
    book, info = load_print_workbook(workbook)
    try:
        grid = build_print_grid(calculation_worksheet(book), columns)
    finally:
        book.close()
    logger.info(
        "Print grid %s sheet=%s dimension=%s kept_rows=%s kept_cols=%s grid=%sx%s in %.2fs",
        workbook,
        info["sheet"],
        info["dimension"] or "none",
        info["rows"],
        info["cols"],
        len(grid.rows),
        len(grid.widths),
        time.perf_counter() - started,
    )

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
    font_name = _ensure_font()
    font_size = 8.0
    padding = 2
    col_widths = content_column_widths(grid, font_name, font_size, padding, usable)
    frame_height = page[1] - (2 * margin)
    sizes = wrap_cells(
        grid, col_widths, font_name, font_size, padding, max_height=frame_height * 0.45
    )
    before = [float(height or 15.0) for height in (grid.row_heights or [15.0] * len(grid.rows))]
    one_line = font_size * 1.2 + 2
    heights = fit_print_row_heights(
        before, grid.repeat_rows, frame_height, one_line, grid.rows
    )
    row_scale = []
    for index, (old, new) in enumerate(zip(before, heights)):
        if grid.repeat_rows and index >= grid.repeat_rows:
            row_scale.append(1.0)
            continue
        row_scale.append((new / old) if old > 1 and new < old - 0.05 else 1.0)
    drawn = measurement_font_size(grid, sizes, row_scale, font_size)
    if grid.repeat_rows < len(heights):
        data_factor = drawn / font_size if font_size else 1.0
        line = drawn * 1.2 + 2
        for index in range(grid.repeat_rows, len(heights)):
            row_scale[index] = data_factor
            row = grid.rows[index] if index < len(grid.rows) else []
            heights[index] = measurement_content_height(row, line)
    sizes = [
        (cell, size * row_scale[cell[1]] if cell[1] < len(row_scale) else size)
        for cell, size in sizes
    ]
    align = cell_alignment(grid)
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
    style += border_commands(grid)
    style += [("ALIGN", cell, cell, "CENTER") for cell in grid.numeric]
    style += [("ALIGN", cell, cell, "CENTER") for cell in grid.centered]
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
    story = [table]
    for blob in sheet_pictures(workbook, info["sheet"]):
        picture = _picture_flowable(blob, usable, frame_height)
        if picture is None:
            continue
        story.append(PageBreak())
        story.append(picture)
    document.build(story)
    logger.info(
        "Wrote %s in %.2fs",
        destination,
        time.perf_counter() - started,
    )


def print_saved_copy(
    workbook: Path,
    orientation: str = "landscape",
    margin_mm: float = 10,
) -> str:
    """Print the PDF from this saved workbook and write it beside that file."""
    source = Path(workbook)
    destination = source.with_suffix(".pdf")
    write_sheet_pdf(source, destination, orientation=orientation, margin_mm=margin_mm)
    return str(destination)


def publish_sheet_pdf(
    source: Path,
    destinations: Iterable[Path],
    orientation: str = "landscape",
    margin_mm: float = 10,
) -> List[str]:
    """Write one PDF from the workbook, then copy it to each Fatina item folder."""
    unique: List[Path] = []
    seen = set()
    for destination in destinations:
        path = Path(destination)
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    if not unique:
        raise ValueError("no Fatina folder")
    first = unique[0]
    first.parent.mkdir(parents=True, exist_ok=True)
    write_sheet_pdf(source, first, orientation=orientation, margin_mm=margin_mm)
    written = [str(first)]
    for destination in unique[1:]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(first, destination)
        logger.info("Copied PDF to %s", destination)
        written.append(str(destination))
    return written


def print_workbooks(
    roots: Iterable[Path],
    orientation: str = "landscape",
    margin_mm: float = 10,
    columns: Optional[List[int]] = None,
) -> PrintBatch:
    """Print every workbook. One bad file is logged and skipped."""
    files: List[str] = []
    errors: List[str] = []
    started = time.perf_counter()
    found: List[Path] = []
    for root in roots:
        if not root.exists():
            logger.warning("Print folder does not exist: %s", root)
            continue
        logger.info("Scanning %s for calculation workbooks", root)
        for workbook in root.rglob("*.xlsx"):
            if workbook.name.startswith("~$"):
                continue
            found.append(workbook)
    logger.info(
        "Printing %s workbook(s), orientation=%s margin_mm=%s",
        len(found),
        orientation,
        margin_mm,
    )
    for index, workbook in enumerate(found, start=1):
        destination = pdf_beside_workbook(workbook)
        try:
            size = workbook.stat().st_size
        except OSError:
            size = -1
        logger.info(
            "[%s/%s] %s (%s bytes) -> %s",
            index,
            len(found),
            workbook,
            size,
            destination,
        )
        try:
            write_sheet_pdf(
                workbook,
                destination,
                orientation=orientation,
                margin_mm=margin_mm,
                columns=columns,
            )
        except Exception as exc:
            logger.exception("Print failed for %s", workbook)
            errors.append(f"{workbook}: {type(exc).__name__}: {exc}")
            continue
        files.append(str(destination))
    logger.info(
        "Print finished: %s pdf(s), %s failed, %.1fs. Failures are listed above.",
        len(files),
        len(errors),
        time.perf_counter() - started,
    )
    return PrintBatch(files=files, errors=errors)
