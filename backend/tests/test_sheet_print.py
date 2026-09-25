import pandas as pd

from services.sheet_print import (
    drop_empty_rows,
    pdf_beside_workbook,
    print_workbooks,
    read_print_frame,
    select_columns,
)
from pathlib import Path


def test_pdf_uses_the_workbook_name_in_the_same_folder():
    workbook = Path("C:/Fatina/1.02/17_1/sheet.xlsx")
    assert pdf_beside_workbook(workbook) == Path("C:/Fatina/1.02/17_1/sheet.pdf")


def test_column_selection_is_one_based():
    frame = pd.DataFrame([[1, 2, 3], [4, 5, 6]])
    chosen = select_columns(frame, [1, 3])
    assert chosen.shape == (2, 2)
    assert list(chosen.iloc[0]) == [1, 3]


def test_empty_rows_are_not_printed():
    frame = pd.DataFrame([["title", None], [None, None], ["1.1", 4]])
    kept = drop_empty_rows(frame)
    assert len(kept) == 2
    assert kept.iloc[0, 0] == "title"


def test_calculation_sheet_is_printed_instead_of_the_first_worksheet(tmp_path):
    folder = tmp_path / "item"
    folder.mkdir()
    workbook = folder / "7.xlsx"
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame([["opening form"]]).to_excel(
            writer, sheet_name="Other", index=False, header=False
        )
        pd.DataFrame([["from-calculation"]]).to_excel(
            writer, sheet_name="Calculation", index=False, header=False
        )
    frame = read_print_frame(workbook)
    assert frame.iloc[0, 0] == "from-calculation"


def test_print_writes_a_pdf_next_to_each_workbook(tmp_path):
    folder = tmp_path / "item" / "17_1"
    folder.mkdir(parents=True)
    frame = pd.DataFrame([["item", "qty"], ["1.1", 3]])
    frame.to_excel(folder / "17_1.xlsx", index=False, header=False)
    written = print_workbooks([tmp_path], orientation="portrait", margin_mm=12, columns=[1, 2])
    assert written == [str(folder / "17_1.pdf")]
    assert (folder / "17_1.pdf").is_file()
