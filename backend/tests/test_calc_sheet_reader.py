from utils.calc_sheet_reader import EMPTY_TAIL, bounded_sheet_rows


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


def test_reader_keeps_detail_lines_after_a_short_gap():
    rows = [(None, None)] * 40
    rows[27] = ("07", 10)
    rows[30] = ("08", 5)
    kept = bounded_sheet_rows(rows)
    assert kept[27][1] == 10
    assert kept[30][1] == 5
