from services.site_work_parser import parse_work_lines


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


def test_ignores_lines_that_are_not_work():
    items = parse_work_lines("See you tomorrow\nThanks", known_systems=["Lighting"])
    assert items == []
