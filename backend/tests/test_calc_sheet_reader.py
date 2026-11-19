import io
import re
import warnings
import zipfile

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.header_footer import HeaderFooterItem
from openpyxl.xml.functions import fromstring

from services.excel_service import _patch_openpyxl_header_footer
from utils.calc_sheet_reader import EMPTY_TAIL, bounded_sheet_rows, load_calculation_sheet_rows


def test_reader_stops_after_an_empty_detail_tail():
    width = 3
    rows = []
    for excel_row in range(1, 28 + EMPTY_TAIL + 5):
        if excel_row == 28:
            rows.append((excel_row, "07", 36.30))
        else:
            rows.append((None, None, None))

    kept = bounded_sheet_rows(rows)
    assert len(kept) == 28 + EMPTY_TAIL
    assert kept[27][2] == 36.30


def _add_extlst_to_pattern_fill(path):
    """Excel writes extLst under patternFill. openpyxl rejects that child."""
    source_bytes = path.read_bytes()
    updated = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as source, zipfile.ZipFile(
        updated, "w"
    ) as dest:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "xl/styles.xml":
                styles = data.decode("utf-8")
                styles, count = re.subn(
                    r"<patternFill([^>]*)/>",
                    r'<patternFill\1><extLst><ext uri="{00000000-0000-0000-0000-000000000000}"/></extLst></patternFill>',
                    styles,
                    count=1,
                )
                assert count == 1
                data = styles.encode("utf-8")
            dest.writestr(item, data)
    path.write_bytes(updated.getvalue())


def test_calculation_sheet_with_excel_fill_extension_still_opens(tmp_path):
    path = tmp_path / "32-7-7.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "Calculation"
    sheet["C1"] = "32/7/7"
    book.save(path)
    book.close()
    _add_extlst_to_pattern_fill(path)

    rows = load_calculation_sheet_rows(str(path))
    assert rows[0][2] == "32/7/7"


def _set_plain_page_footer(path):
    """Excel stores this footer with no &L, &C, or &R section code."""
    source_bytes = path.read_bytes()
    updated = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as source, zipfile.ZipFile(
        updated, "w"
    ) as dest:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                sheet = data.decode("utf-8")
                footer = (
                    "<headerFooter><oddFooter>Page &amp;P of &amp;N</oddFooter></headerFooter>"
                )
                sheet = sheet.replace("</worksheet>", footer + "</worksheet>")
                data = sheet.encode("utf-8")
            dest.writestr(item, data)
    path.write_bytes(updated.getvalue())


def test_plain_page_footer_is_kept():
    _patch_openpyxl_header_footer()
    node = fromstring("<oddFooter>Page &amp;P of &amp;N</oddFooter>")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        footer = HeaderFooterItem.from_tree(node)
    assert footer.center.text == "Page &P of &N"
    assert not any("header or footer" in str(item.message) for item in caught)

    sections = fromstring(
        "<oddHeader>&amp;Rright&amp;Lleft&amp;Cmiddle</oddHeader>"
    )
    header = HeaderFooterItem.from_tree(sections)
    assert header.left.text == "left"
    assert header.center.text == "middle"
    assert header.right.text == "right"


def test_calculation_sheet_with_plain_footer_opens_quietly(tmp_path):
    path = tmp_path / "32-7-7.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "Calculation"
    sheet["C1"] = "32/7/7"
    book.save(path)
    book.close()
    _set_plain_page_footer(path)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        rows = load_calculation_sheet_rows(str(path))
        opened = load_workbook(path, data_only=True)
    assert rows[0][2] == "32/7/7"
    assert opened["Calculation"].oddFooter.center.text == "Page &P of &N"
    opened.close()
    assert not any("header or footer" in str(item.message) for item in caught)


def test_reader_keeps_detail_lines_after_a_short_gap():
    rows = [(None, None)] * 40
    rows[27] = ("07", 10)
    rows[30] = ("08", 5)
    kept = bounded_sheet_rows(rows)
    assert kept[27][1] == 10
    assert kept[30][1] == 5
