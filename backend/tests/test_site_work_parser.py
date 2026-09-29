from services.site_work_parser import classification_after_system_change, parse_work_lines


def test_categorizes_contract_systems_and_dedupes():
    text = """
    Lighting poles along the road
    Lighting poles along the road
    ניקוז תעלה צפונית
    hello
    """
    items = parse_work_lines(text, known_systems=["בטון"])
    assert [item["system_name"] for item in items] == ["Lighting", "Drainage"]
    assert all(item["classification"] == "system" for item in items)
    assert len(items) == 2


def test_exception_and_additional_work():
    text = "Exception: night concrete pour\nAdditional work — extra drainage channel"
    items = parse_work_lines(text, known_systems=[])
    by_class = {item["classification"]: item for item in items}
    assert by_class["exception"]["system_name"] == "Concrete"
    assert by_class["additional_work"]["system_name"] == "Drainage"


def test_prefers_system_name_already_on_the_contract():
    text = "יציקת בטון קיר DC-36"
    items = parse_work_lines(text, known_systems=["בטון"])
    assert items[0]["system_name"] == "בטון"
    assert items[0]["classification"] == "system"


def test_ignores_greetings():
    items = parse_work_lines("Thanks\nhello", known_systems=["Lighting"])
    assert items == []


def test_changing_exception_to_a_contract_system():
    assert classification_after_system_change("exception", "Drainage") == "system"
    assert classification_after_system_change("system", "Exception") == "exception"
    assert classification_after_system_change("additional_work", "Lighting") == "additional_work"


def test_uncategorized_job_is_exception():
    items = parse_work_lines("Repair the north gate hinge", known_systems=["Lighting", "בטון"])
    assert len(items) == 1
    assert items[0]["system_name"] == "Exception"
    assert items[0]["classification"] == "exception"
