from types import SimpleNamespace

from utils.fatina_invoice_isolation import invoices_exclusive_to_other_items


def test_drops_invoice_that_belongs_only_to_another_item():
    entries = [
        SimpleNamespace(section_number="1.51.02.0020", current_invoice_id="07"),
        SimpleNamespace(section_number="1.51.02.0030", current_invoice_id="05"),
    ]
    assert invoices_exclusive_to_other_items(entries, "1.51.02.0030") == {"07"}
    assert invoices_exclusive_to_other_items(entries, "1.51.02.0020") == {"05"}


def test_keeps_invoice_when_this_item_also_uses_it():
    entries = [
        SimpleNamespace(section_number="1.51.02.0020", current_invoice_id="06"),
        SimpleNamespace(section_number="1.51.02.0030", current_invoice_id="06"),
    ]
    assert invoices_exclusive_to_other_items(entries, "1.51.02.0030") == set()
