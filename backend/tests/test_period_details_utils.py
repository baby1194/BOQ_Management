from types import SimpleNamespace

from utils.concentration_utils import apply_calculation_entry_quantities
from utils.period_details_utils import (
    apply_current_period_to_entry_fields,
    entry_total_approved_quantity,
    entry_total_internal_quantity,
    hydrate_entry_period_details,
    merge_breakdown_preserve_period_details,
    migrate_entry_period_details,
    persist_entry_level_fields_to_period,
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


def test_new_invoice_period_starts_with_empty_editable_fields():
    entry = SimpleNamespace(
        drawing_no="02",
        internal_quantity=8.0,
        approved_by_project_manager=6.0,
        notes="stale top-level",
        supervisor_notes="",
        submission_percentage=100.0,
        drawing_files=[],
        submission_breakdown={
            "current_drawing_no": "02",
            "periods": {"01": 10.0, "02": 5.0},
            "period_details": {
                "01": {
                    "internal_quantity": 8.0,
                    "approved_by_project_manager": 6.0,
                    "notes": "invoice 01",
                    "supervisor_notes": "",
                    "drawing_files": [],
                }
            },
        },
    )

    migrate_entry_period_details(entry)
    apply_current_period_to_entry_fields(entry)

    assert entry.submission_breakdown["period_details"]["02"]["approved_by_project_manager"] == 0.0
    assert entry.submission_breakdown["period_details"]["02"]["internal_quantity"] == 0.0
    assert entry.approved_by_project_manager == 0.0
    assert entry.internal_quantity == 0.0
    assert entry_total_approved_quantity(entry) == 6.0


def test_apply_calculation_entry_quantities_resets_new_invoice_approved_qty():
    concentration_entry = SimpleNamespace(
        drawing_no="01",
        estimated_quantity=100.0,
        quantity_submitted=10.0,
        submission_percentage=10.0,
        internal_quantity=8.0,
        approved_by_project_manager=6.0,
        notes="invoice 01",
        supervisor_notes="",
        drawing_files=[],
        submission_breakdown={
            "current_drawing_no": "01",
            "periods": {"01": 10.0},
            "period_details": {
                "01": {
                    "internal_quantity": 8.0,
                    "approved_by_project_manager": 6.0,
                    "notes": "invoice 01",
                    "supervisor_notes": "",
                    "drawing_files": [],
                }
            },
        },
    )
    calc_entry = SimpleNamespace(
        estimated_quantity=100.0,
        quantity_submitted=5.0,
        submission_breakdown={
            "current_drawing_no": "02",
            "periods": {"01": 10.0, "02": 5.0},
        },
    )

    apply_calculation_entry_quantities(
        concentration_entry, calc_entry, drawing_no="02"
    )

    assert concentration_entry.drawing_no == "02"
    assert concentration_entry.approved_by_project_manager == 0.0
    assert (
        concentration_entry.submission_breakdown["period_details"]["01"][
            "approved_by_project_manager"
        ]
        == 6.0
    )
    assert (
        concentration_entry.submission_breakdown["period_details"]["02"][
            "approved_by_project_manager"
        ]
        == 0.0
    )


def test_persist_entry_level_fields_to_period_before_invoice_switch():
    entry = SimpleNamespace(
        drawing_no="01",
        internal_quantity=3.0,
        approved_by_project_manager=2.0,
        notes="invoice 01",
        supervisor_notes="",
        submission_percentage=100.0,
        drawing_files=[],
        submission_breakdown={
            "current_drawing_no": "01",
            "periods": {"01": 10.0},
        },
    )

    assert persist_entry_level_fields_to_period(entry, "01") is True
    assert entry.submission_breakdown["period_details"]["01"]["approved_by_project_manager"] == 2.0


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


def test_set_period_detail_fields_seeds_from_entry_when_creating_period():
    """Drawing-file-only updates must not wipe existing top-level quantities."""
    entry = SimpleNamespace(
        drawing_no="01",
        internal_quantity=33.0,
        approved_by_project_manager=22.0,
        notes="keep",
        supervisor_notes="sup",
        submission_percentage=100.0,
        drawing_files=[],
        submission_breakdown=None,
        current_invoice_id=None,
    )
    set_period_detail_fields(
        entry,
        "01",
        {"drawing_files": ["/tmp/a.png"]},
    )
    assert entry.internal_quantity == 33.0
    assert entry.approved_by_project_manager == 22.0
    assert entry.notes == "keep"
    detail = entry.submission_breakdown["period_details"]["01"]
    assert detail["internal_quantity"] == 33.0
    assert detail["approved_by_project_manager"] == 22.0
    assert detail["drawing_files"] == ["/tmp/a.png"]


def test_hydrate_preserves_qty_update_when_only_period_details_exist():
    """Qty edits must write period_details even when periods key is missing."""
    entry = SimpleNamespace(
        drawing_no="01",
        internal_quantity=0.0,
        approved_by_project_manager=0.0,
        notes="",
        supervisor_notes="",
        submission_percentage=100.0,
        drawing_files=[],
        current_invoice_id=None,
        submission_breakdown={
            "period_details": {
                "01": {
                    "internal_quantity": 0.0,
                    "approved_by_project_manager": 0.0,
                    "notes": "",
                    "supervisor_notes": "",
                    "drawing_files": ["/tmp/a.png"],
                }
            }
        },
    )
    set_period_detail_fields(
        entry,
        "01",
        {"internal_quantity": 50.0, "approved_by_project_manager": 40.0},
    )
    hydrate_entry_period_details(entry)
    assert entry.internal_quantity == 50.0
    assert entry.approved_by_project_manager == 40.0
    assert (
        entry.submission_breakdown["period_details"]["01"]["internal_quantity"]
        == 50.0
    )
