from types import SimpleNamespace

from services.overrun_export import (
    current_contract_quantity,
    first_invoice_over_contract,
    period_quantities,
)


def test_first_crossing_invoice_matches_client_example():
    # Contract 78; invoice 07 submitted 103.652, which is already over.
    assert first_invoice_over_contract({"07": 103.652}, 78) == "07"


def test_running_total_uses_invoice_order_not_dict_order():
    assert first_invoice_over_contract({"08": 40, "01": 50, "02": 30}, 78) == "02"


def test_under_contract_has_no_invoice():
    assert first_invoice_over_contract({"01": 40, "02": 30}, 78) is None


def test_period_quantities_sum_entries():
    entries = [
        SimpleNamespace(submission_breakdown={"periods": {"07": 100}}, drawing_no="07", quantity_submitted=100),
        SimpleNamespace(submission_breakdown={"periods": {"07": 3.652, "08": 10}}, drawing_no="08", quantity_submitted=10),
    ]
    totals = period_quantities(entries)
    assert totals["07"] == 103.652
    assert first_invoice_over_contract(totals, 78) == "07"


def test_current_contract_quantity_prefers_latest_update():
    item = SimpleNamespace(original_contract_quantity=78)
    updates = [
        SimpleNamespace(
            updated_contract_quantity=90,
            contract_update=SimpleNamespace(update_index=1),
        ),
        SimpleNamespace(
            updated_contract_quantity=80,
            contract_update=SimpleNamespace(update_index=2),
        ),
    ]
    assert current_contract_quantity(item, updates) == 80
    assert current_contract_quantity(item, []) == 78
