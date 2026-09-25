from utils.contract_update_flags import (
    has_changed_contract_quantity,
    resolved_contract_quantity_for_new_update,
)


def test_first_update_marks_when_quantity_changes_from_original():
    assert has_changed_contract_quantity(
        original_quantity=200,
        latest_quantity=250,
        previous_quantity=None,
        has_latest_row=True,
    )


def test_second_update_hides_badge_when_quantity_unchanged():
    assert not has_changed_contract_quantity(
        original_quantity=200,
        latest_quantity=250,
        previous_quantity=250,
        has_latest_row=True,
    )


def test_second_update_shows_badge_when_quantity_changes_again():
    assert has_changed_contract_quantity(
        original_quantity=200,
        latest_quantity=300,
        previous_quantity=250,
        has_latest_row=True,
    )


def test_no_latest_row_hides_badge():
    assert not has_changed_contract_quantity(
        original_quantity=200,
        latest_quantity=None,
        previous_quantity=None,
        has_latest_row=False,
    )


def test_new_update_row_carries_forward_previous_quantity():
    qty, total = resolved_contract_quantity_for_new_update(
        original_quantity=200,
        price=10,
        previous_updated_quantity=454.41,
        previous_updated_sum=5000,
    )
    assert qty == 454.41
    assert total == 5000


def test_new_update_row_uses_original_when_no_previous():
    qty, total = resolved_contract_quantity_for_new_update(
        original_quantity=200,
        price=10,
        previous_updated_quantity=None,
    )
    assert qty == 200
    assert total == 2000
