from services.sheet_system_filter import sheet_ids_for_system


def test_sheets_that_contain_the_system():
    boq = [("1.08.10.3296", "Lighting"), ("1.51.01.0570", "Drainage")]
    entries = [(10, "1.08.10.3296"), (10, "1.51.01.0570"), (11, "1.51.01.0570")]
    assert sheet_ids_for_system(boq, entries, "Lighting") == [10]
    assert sheet_ids_for_system(boq, entries, "drainage") == [10, 11]


def test_unknown_system_has_no_sheets():
    assert sheet_ids_for_system([("1.1", "Lighting")], [(3, "1.1")], "Exception") == []
