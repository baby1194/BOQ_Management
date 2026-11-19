import io
import re
import zipfile
from pathlib import Path

from bidi.algorithm import get_display
from openpyxl import Workbook
from reportlab.lib import colors

from fatina_paths import calculation_sheet_pdf_destinations
from services.sheet_print import (
    border_commands,
    build_print_grid,
    calculation_worksheet,
    filled_cell_boxes,
    format_cell,
    cell_alignment,
    load_print_workbook,
    pdf_beside_workbook,
    print_workbooks,
    publish_sheet_pdf,
)


def test_pdf_uses_the_workbook_name_in_the_same_folder():
    workbook = Path("C:/Fatina/1.02/17_1/sheet.xlsx")
    assert pdf_beside_workbook(workbook) == Path("C:/Fatina/1.02/17_1/sheet.pdf")


def test_numbers_have_no_float_noise():
    assert format_cell(13.850000000000001) == "13.85"
    assert format_cell(4.0) == "4"
    assert format_cell(0.1 + 0.2) == "0.3"
    assert format_cell(None) == ""


def test_only_the_filled_block_is_printed():
    book = Workbook()
    ws = book.active
    ws["C3"] = "item"
    ws["E3"] = "qty"
    ws["C5"] = "1.1"
    ws["E5"] = 13.850000000000001
    grid = build_print_grid(ws)
    assert grid.rows == [["item", "qty"], ["1.1", "13.85"]]
    assert grid.right_to_left is False


def test_hebrew_sheet_prints_right_to_left():
    book = Workbook()
    ws = book.active
    ws.sheet_view.rightToLeft = True
    ws["A1"] = "סעיף"
    ws["B1"] = "כמות"
    ws["A2"] = "1.1"
    ws["B2"] = 3
    grid = build_print_grid(ws)
    assert grid.right_to_left is True
    assert grid.rows[0] == ["תומכ", "ףיעס"]
    assert grid.rows[1] == ["3", "1.1"]


def test_print_area_limits_the_block():
    book = Workbook()
    ws = book.active
    ws["A1"] = "keep"
    ws["B1"] = "keep too"
    ws["D1"] = "outside"
    ws.print_area = "A1:B1"
    assert build_print_grid(ws).rows == [["keep", "keep too"]]


def test_merged_title_spans_the_kept_columns():
    book = Workbook()
    ws = book.active
    ws["A1"] = "title"
    ws.merge_cells("A1:C1")
    ws["A2"] = "a"
    ws["B2"] = "b"
    ws["C2"] = "c"
    grid = build_print_grid(ws)
    assert grid.spans == [((0, 0), (2, 0))]


def test_a_long_sheet_repeats_its_title_and_keeps_the_table_columns():
    book = Workbook()
    ws = book.active
    ws["A1"] = "title"
    ws["C28"] = "item"
    ws["E28"] = 4
    grid = build_print_grid(ws)
    assert grid.repeat_rows == 27
    assert len(grid.rows) == 28
    assert grid.rows[0] == ["title", "", "", ""]
    assert grid.rows[1] == ["", "", "", ""]
    assert grid.rows[26] == ["", "", "", ""]
    assert grid.rows[27] == ["", "item", "", "4"]
    assert all(len(row) == 4 for row in grid.rows)


def test_item_numbers_and_descriptions_are_centered():
    book = Workbook()
    ws = book.active
    ws.sheet_view.rightToLeft = True
    ws["R2"] = "05"
    ws["B3"] = "תאור העבודה"
    ws["R3"] = "264-290 L"
    ws["B4"] = "מס' סעיף"
    ws["O4"] = "1.51.02.0020"
    ws["R4"] = "1.51.02.0030"
    ws["B5"] = "תיאור סעיף"
    ws["R5"] = "חפירה לאורך הדרך"
    ws["B6"] = "יחידה"
    ws["R6"] = 'מ"ק'
    ws["B8"] = "שם פרויקט"
    ws["C8"] = "כביש 40"
    ws["C28"] = "09"
    ws["D28"] = 4
    grid = build_print_grid(ws)
    centered = {grid.rows[row][column] for column, row in grid.centered}
    assert "05" in centered
    assert "264-290 L" in centered
    assert "1.51.02.0030" in centered
    assert "1.51.02.0020" in centered
    assert get_display("חפירה לאורך הדרך") in centered
    assert get_display('מ"ק') in centered
    assert get_display("כביש 40") not in centered


def test_every_word_is_centered_in_its_cell():
    book = Workbook()
    ws = book.active
    ws.sheet_view.rightToLeft = True
    ws["A1"] = "שם פרויקט"
    ws["B1"] = "כביש 40"
    ws["A2"] = "L"
    grid = build_print_grid(ws)
    assert grid.right_to_left is True
    assert cell_alignment(grid) == "CENTER"


def test_measurement_column_titles_are_centered():
    book = Workbook()
    ws = book.active
    ws.sheet_view.rightToLeft = True
    ws["C27"] = "שטח חפירה"
    ws["D27"] = "צד"
    ws["E27"] = "חתך"
    ws["C28"] = "09"
    ws["D28"] = "L"
    ws["E28"] = 95
    grid = build_print_grid(ws)
    centered = {grid.rows[row][column] for column, row in grid.centered}
    assert get_display("שטח חפירה") in centered
    assert get_display("צד") in centered
    assert get_display("חתך") in centered
    assert cell_alignment(grid) == "CENTER"


def test_a_short_sheet_does_not_pad_empty_title_rows():
    book = Workbook()
    ws = book.active
    ws["A1"] = "only"
    ws["B3"] = 2
    grid = build_print_grid(ws)
    assert grid.repeat_rows == 0
    assert grid.rows == [["only", ""], ["", "2"]]


def test_table_prints_through_the_last_value_in_column_c_with_full_borders():
    book = Workbook()
    ws = book.active
    ws["B5"] = "title"
    ws["C27"] = "account"
    ws["D27"] = "length"
    ws["C28"] = "09"
    ws["D28"] = 4
    ws["D29"] = 1
    ws["C30"] = "10"
    ws["D30"] = 2
    ws["D31"] = 99
    grid = build_print_grid(ws)
    assert grid.repeat_rows == 27
    assert grid.table_start == 26
    assert len(grid.rows) == 30
    assert grid.rows[4] == ["title", "", ""]
    assert grid.rows[26] == ["", "account", "length"]
    assert grid.rows[28] == ["", "", "1"]
    assert grid.rows[29] == ["", "10", "2"]
    assert all("99" not in row for row in grid.rows)
    boxes = filled_cell_boxes(grid.rows, grid.spans, grid.table_start, grid.table_columns)
    assert ((0, 4), (0, 4)) in boxes
    assert ((1, 4), (1, 4)) not in boxes
    assert ((1, 28), (1, 28)) in boxes
    assert ((2, 28), (2, 28)) in boxes
    commands = border_commands(grid)
    assert ("GRID", (1, 26), (2, 29), 0.25, colors.grey) in commands
    assert not any(command[0] == "BOX" and command[1][1] >= 26 for command in commands)


def test_repeated_title_leaves_room_for_several_measurement_rows():
    from services.sheet_print import _heights_that_fit

    heights = [40.0] * 20 + [18.0] * 100
    frame = 538.0
    fitted = _heights_that_fit(heights, 20, frame)
    header = sum(fitted[:20])
    assert header <= frame * 0.42 + 0.1
    assert fitted[20] == 18.0
    assert frame - header - 8 > 18.0 * 8


def test_measurement_font_matches_the_shrunk_title_text():
    from services.sheet_print import PrintGrid, measurement_font_size

    grid = PrintGrid(
        rows=[["title text", ""], ["8"]],
        widths=[20, 20],
        right_to_left=False,
        repeat_rows=1,
    )
    # The title cell was shrunk to 4, then the row was scaled by half.
    size = measurement_font_size(grid, [((0, 0), 4.0)], [0.5, 1.0], 8.0)
    assert abs(size - 2.0) < 0.001


def test_measurement_font_matches_the_title_scale():
    from services.sheet_print import _title_font_scale

    before = [40.0] * 27 + [36.0] * 3
    heights = [20.0] * 27 + [11.6] * 3
    assert abs(_title_font_scale(before, heights, 27) - 0.5) < 0.001


def test_measurement_lines_are_one_row_tall():
    from services.sheet_print import fit_print_row_heights

    heights = [40.0] * 27 + [36.0] * 5
    fitted = fit_print_row_heights(heights, 27, 538.0, 11.6)
    assert fitted[26] != 11.6
    assert fitted[27:] == [11.6] * 5


def test_long_text_wraps_inside_its_cell():
    from services.sheet_print import _ensure_font, wrap_cells

    book = Workbook()
    ws = book.active
    ws["A1"] = "one two three four"
    ws["B1"] = "keep"
    grid = build_print_grid(ws)
    wrap_cells(grid, [40, 80], _ensure_font(), 8, 2)
    assert "\n" in grid.rows[0][0]
    assert grid.rows[0][1] == "keep"
    assert grid.row_heights[0] > 15


def test_borders_are_only_drawn_around_filled_cells():
    boxes = filled_cell_boxes(
        [["title", "", ""], ["", "1", ""]],
        [((0, 0), (1, 0))],
    )
    assert boxes == [((0, 0), (1, 0)), ((1, 1), (1, 1))]


def test_calculation_sheet_is_printed_instead_of_the_first_worksheet():
    book = Workbook()
    book.active.title = "Other"
    book.create_sheet("Calculation")
    assert calculation_worksheet(book).title == "Calculation"


def test_print_writes_a_pdf_next_to_each_workbook(tmp_path):
    folder = tmp_path / "item" / "17_1"
    folder.mkdir(parents=True)
    book = Workbook()
    ws = book.active
    ws.title = "Calculation"
    ws.append(["סעיף", "כמות"])
    ws.append(["1.1", 3])
    book.save(folder / "17_1.xlsx")
    written = print_workbooks([tmp_path], orientation="portrait", margin_mm=0, columns=[1, 2])
    assert written.files == [str(folder / "17_1.pdf")]
    assert written.errors == []
    assert (folder / "17_1.pdf").is_file()


def _add_phantom_last_row(path: Path) -> None:
    """Excel's used range can claim row 1048576 even though the sheet ends much earlier."""
    source_bytes = path.read_bytes()
    updated = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as source, zipfile.ZipFile(
        updated, "w"
    ) as dest:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                sheet = data.decode("utf-8")
                sheet, count = re.subn(
                    r'(<dimension[^>]*ref=")[^"]+"',
                    r'\1A1:C1048576"',
                    sheet,
                    count=1,
                )
                assert count == 1
                phantom = (
                    '<row r="1048576"><c r="C1048576"><v>999</v></c></row></sheetData>'
                )
                assert "</sheetData>" in sheet
                sheet = sheet.replace("</sheetData>", phantom, 1)
                data = sheet.encode("utf-8")
            dest.writestr(item, data)
    path.write_bytes(updated.getvalue())


def test_print_stops_before_a_phantom_millionth_row(tmp_path):
    path = tmp_path / "01-2.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "Calculation"
    sheet["C1"] = "32/7/7"
    sheet["C28"] = "09"
    sheet["D28"] = 4
    book.save(path)
    book.close()
    _add_phantom_last_row(path)

    loaded, info = load_print_workbook(path)
    try:
        grid = build_print_grid(calculation_worksheet(loaded))
    finally:
        loaded.close()
    assert info["rows"] < 500
    assert loaded is not None
    assert all("999" not in row for row in grid.rows)
    assert any("09" in row for row in grid.rows)


def test_pdf_destinations_follow_the_concentration_items():
    destinations = calculation_sheet_pdf_destinations(
        ["01.02.01.0010", "01.02.01.0010", "08.10"],
        "12",
        "12.xlsx",
    )
    assert [path.as_posix() for path in destinations] == [
        "C:/Fatina/01.02.01.0010/12/12.pdf",
        "C:/Fatina/08.10/12/12.pdf",
    ]


def test_one_workbook_is_copied_into_each_item_folder(tmp_path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    book = Workbook()
    book.active.title = "Calculation"
    book.active["A1"] = "only"
    book.save(source_dir / "12.xlsx")
    book.close()
    first = tmp_path / "item-a" / "12" / "12.pdf"
    second = tmp_path / "item-b" / "12" / "12.pdf"

    written = publish_sheet_pdf(source_dir / "12.xlsx", [first, second])

    assert written == [str(first), str(second)]
    assert first.is_file()
    assert second.is_file()
    assert first.read_bytes() == second.read_bytes()


def test_one_bad_workbook_does_not_stop_the_rest(tmp_path):
    folder = tmp_path / "good"
    folder.mkdir()
    book = Workbook()
    book.active.title = "Calculation"
    book.active["A1"] = "ok"
    book.save(folder / "ok.xlsx")
    book.close()
    (tmp_path / "bad.xlsx").write_bytes(b"not a workbook")

    written = print_workbooks([tmp_path])
    assert written.files == [str(folder / "ok.pdf")]
    assert len(written.errors) == 1
    assert "bad.xlsx" in written.errors[0]
