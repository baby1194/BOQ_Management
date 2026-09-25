import pandas as pd

from services.non_boq_service import build_non_boq_import_rows
from utils.calculation_sheet_utils import read_non_boq_price


def test_price_is_read_from_excel_row_7():
    df = pd.DataFrame([[None] * 6 for _ in range(8)])
    df.iloc[6, 4] = 1213
    assert read_non_boq_price(df, 4) == 1213


def test_import_rows_sum_quantity_and_keep_the_first_price():
    rows = build_non_boq_import_rows(
        [
            {
                "section_number": "99.02.01.0640",
                "description": "Extra wall",
                "estimated_quantity": 10,
                "unit_price": 50,
            },
            {
                "section_number": "99.02.01.0640",
                "description": "",
                "estimated_quantity": 2.5,
                "unit_price": 80,
            },
            {
                "section_number": "99.05.031.0012",
                "description": "",
                "estimated_quantity": 4,
                "unit_price": None,
            },
        ]
    )
    by_section = {row["section_number"]: row for row in rows}
    assert by_section["99.02.01.0640"]["quantity"] == 12.5
    assert by_section["99.02.01.0640"]["price"] == 50
    assert by_section["99.02.01.0640"]["total"] == 625
    assert by_section["99.05.031.0012"]["description"] == "99.05.031.0012"
    assert by_section["99.05.031.0012"]["missing_price"] is True
