from types import SimpleNamespace

from utils.period_details_utils import (
    apply_current_period_to_entry_fields,
    entry_total_approved_quantity,
    entry_total_internal_quantity,
    merge_breakdown_preserve_period_details,
    migrate_entry_period_details,
    set_period_detail_fields,
)


def test_merge_breakdown_preserves_period_details():
    old = {
        "current_drawing_no": "01",
        "periods": {"01": 10.0},
        "period_details": {
            "01": {
                "internal_quantity": 5.0,
                "approved_by_project_manager": 4.0,
                "notes": "invoice 01",
            }
        },
    }
    new = {
        "current_drawing_no": "02",
        "periods": {"01": 10.0, "02": 8.0},
    }
    merged = merge_breakdown_preserve_period_details(old, new)
    assert merged["current_drawing_no"] == "02"
    assert merged["period_details"]["01"]["internal_quantity"] == 5.0


def test_invoice_specific_values_persist_when_current_changes():
    entry = SimpleNamespace(
        drawing_no="02",
        internal_quantity=99.0,
        approved_by_project_manager=88.0,
        notes="current",
        supervisor_notes="",
        submission_percentage=100.0,
        drawing_files=[],
        submission_breakdown={
            "current_drawing_no": "02",
            "periods": {"01": 10.0, "02": 8.0},
            "period_details": {
                "01": {
                    "internal_quantity": 5.0,
                    "approved_by_project_manager": 4.0,
                    "notes": "invoice 01",
                    "supervisor_notes": "",
                    "drawing_files": [],
                },
                "02": {
                    "internal_quantity": 2.0,
                    "approved_by_project_manager": 1.0,
                    "notes": "invoice 02",
                    "supervisor_notes": "",
                    "drawing_files": [],
                },
            },
        },
    )

    apply_current_period_to_entry_fields(entry)
    assert entry.internal_quantity == 2.0
    assert entry.notes == "invoice 02"
    assert entry_total_internal_quantity(entry) == 7.0
    assert entry_total_approved_quantity(entry) == 5.0


def test_migrate_legacy_entry_fields_into_current_period():
    entry = SimpleNamespace(
        drawing_no="01",
        internal_quantity=3.0,
        approved_by_project_manager=2.0,
        notes="legacy",
        supervisor_notes="sup",
        submission_percentage=100.0,
        drawing_files=["/tmp/a.pdf"],
        submission_breakdown={
            "current_drawing_no": "01",
            "periods": {"01": 10.0},
        },
    )
    assert migrate_entry_period_details(entry) is True
    details = entry.submission_breakdown["period_details"]["01"]
    assert details["internal_quantity"] == 3.0
    assert details["notes"] == "legacy"
    assert details["drawing_files"] == ["/tmp/a.pdf"]


def test_set_period_detail_fields_updates_current_top_level():
    entry = SimpleNamespace(
        drawing_no="01",
        internal_quantity=0.0,
        approved_by_project_manager=0.0,
        notes=None,
        supervisor_notes=None,
        submission_percentage=100.0,
        drawing_files=[],
        submission_breakdown={
            "current_drawing_no": "01",
            "periods": {"01": 10.0},
            "period_details": {},
        },
    )
    set_period_detail_fields(
        entry,
        "01",
        {
            "internal_quantity": 6.0,
            "approved_by_project_manager": 5.0,
            "notes": "saved",
        },
    )
    assert entry.internal_quantity == 6.0
    assert entry.notes == "saved"
