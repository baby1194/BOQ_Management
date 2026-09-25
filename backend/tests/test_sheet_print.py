import pandas as pd

from services.sheet_print import pdf_beside_workbook, print_workbooks, select_columns
from pathlib import Path


def test_pdf_uses_the_workbook_name_in_the_same_folder():
    workbook = Path("C:/Fatina/1.02/17_1/sheet.xlsx")
    assert pdf_beside_workbook(workbook) == Path("C:/Fatina/1.02/17_1/sheet.pdf")


def test_column_selection_is_one_based():
    frame = pd.DataFrame([[1, 2, 3], [4, 5, 6]])
    chosen = select_columns(frame, [1, 3])
    assert chosen.shape == (2, 2)
    assert list(chosen.iloc[0]) == [1, 3]


def test_print_writes_a_pdf_next_to_each_workbook(tmp_path):
    folder = tmp_path / "item" / "17_1"
    folder.mkdir(parents=True)
    frame = pd.DataFrame([["item", "qty"], ["1.1", 3]])
    frame.to_excel(folder / "17_1.xlsx", index=False, header=False)
    written = print_workbooks([tmp_path], orientation="portrait", margin_mm=12, columns=[1, 2])
    assert written == [str(folder / "17_1.pdf")]
    assert (folder / "17_1.pdf").is_file()
