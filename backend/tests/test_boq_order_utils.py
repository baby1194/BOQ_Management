"""Tests for BOQ serial-number / display-order helpers."""

from types import SimpleNamespace

from utils.boq_order_utils import (
    assign_serial_numbers_by_display_order,
    boq_item_display_sort_key,
    boq_item_serial_sort_key,
    place_item_at_serial_position,
    sort_concentration_sheets_by_boq_order,
)


def _boq(id: int, serial_number=None, display_order=0):
    return SimpleNamespace(
        id=id,
        serial_number=serial_number,
        display_order=display_order,
    )


def _sheet(id: int, boq_item_id: int):
    return SimpleNamespace(id=id, boq_item_id=boq_item_id)


class _FakeQuery:
    def __init__(self, items):
        self._items = items

    def filter(self, *_args, **_kwargs):
        return self

    def all(self):
        return list(self._items)


class _FakeSession:
    def __init__(self, boq_items):
        self._boq_items = boq_items

    def query(self, model):
        assert model.__name__ == "BOQItem"
        return _FakeQuery(self._boq_items)


def test_boq_item_serial_sort_key_orders_by_serial_then_id():
    items = [_boq(3, 10), _boq(1, 5), _boq(2, 5)]
    assert sorted(items, key=boq_item_serial_sort_key) == [
        _boq(1, 5),
        _boq(2, 5),
        _boq(3, 10),
    ]


def test_boq_item_serial_sort_key_puts_null_serial_last():
    items = [_boq(2, None), _boq(1, 1)]
    assert sorted(items, key=boq_item_serial_sort_key) == [
        _boq(1, 1),
        _boq(2, None),
    ]


def test_assign_serial_numbers_follows_display_order():
    items = [
        _boq(30, 301, display_order=1),
        _boq(10, 357, display_order=0),
        _boq(20, 12, display_order=2),
    ]
    assign_serial_numbers_by_display_order(items)
    by_id = {item.id: item.serial_number for item in items}
    assert by_id == {10: 1, 30: 2, 20: 3}


def test_place_item_renumbers_one_through_count():
    items = [
        _boq(10, 357, display_order=0),
        _boq(30, 301, display_order=1),
        _boq(20, 12, display_order=2),
    ]
    place_item_at_serial_position(items, 20, 1)
    ordered = sorted(items, key=lambda item: item.display_order)
    assert [item.id for item in ordered] == [20, 10, 30]
    assert [item.serial_number for item in ordered] == [1, 2, 3]


def test_sort_concentration_sheets_by_boq_order():
    boq_items = [
        _boq(10, 1, display_order=0),
        _boq(20, 2, display_order=1),
        _boq(30, 5, display_order=2),
    ]
    sheets = [
        _sheet(3, 30),
        _sheet(1, 10),
        _sheet(2, 20),
    ]
    db = _FakeSession(boq_items)
    ordered = sort_concentration_sheets_by_boq_order(sheets, db)
    assert [sheet.id for sheet in ordered] == [1, 2, 3]
