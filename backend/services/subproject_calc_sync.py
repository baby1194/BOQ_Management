"""Keep a sub-project copy in step with a main-project calculation sheet.

Non-BOQ items copied into a sub-project take their calculation sheet with them.
A later quantity or price change on the main sheet stays there until someone
asks to copy it across. Deleting the main sheet leaves the sub-project copy
until someone asks to remove that too.
"""

from __future__ import annotations

import copy
import json
import logging
from typing import Iterable, Optional

from sqlalchemy.orm import Session, sessionmaker

from database import project_registry
from models import models
from services.calculation_sheet_sync import push_calculation_sheet_to_concentration_entries
from services.project_rollup import linked_project_ids
from services.sync_service import SyncService
from utils.quantity_utils import round_quantity

logger = logging.getLogger(__name__)


def _normalize(value) -> str:
    return str(value or "").strip()


def _read(entry, key):
    if isinstance(entry, dict):
        return entry.get(key)
    return getattr(entry, key, None)


def _money(value) -> Optional[float]:
    """Row 7 price. An empty cell and a zero are both 'no price'."""
    if value is None or value == "":
        return None
    try:
        number = round(float(value), 2)
    except (TypeError, ValueError):
        return None
    if number == 0:
        return None
    return number


def _breakdown_fingerprint(breakdowns: list) -> str:
    normalized = [item if item else None for item in breakdowns]
    return json.dumps(normalized, sort_keys=True, default=str)


def _section_states(entries: Iterable) -> dict[str, dict]:
    states: dict[str, dict] = {}
    for entry in entries:
        section = _normalize(_read(entry, "section_number"))
        if not section:
            continue
        slot = states.setdefault(
            section,
            {
                "estimated": 0.0,
                "submitted": 0.0,
                "price": None,
                "breakdowns": [],
            },
        )
        slot["estimated"] = round_quantity(
            slot["estimated"] + float(_read(entry, "estimated_quantity") or 0)
        )
        slot["submitted"] = round_quantity(
            slot["submitted"] + float(_read(entry, "quantity_submitted") or 0)
        )
        if slot["price"] is None:
            money = _money(_read(entry, "unit_price"))
            if money is not None:
                slot["price"] = money
        breakdown = _read(entry, "submission_breakdown")
        slot["breakdowns"].append(breakdown if breakdown else None)
    return states


def capture_sheet_entries(db: Session, sheet_id: int) -> list[dict]:
    """Plain copy of one sheet's rows, taken before those rows are replaced."""
    rows = (
        db.query(models.CalculationEntry)
        .filter(models.CalculationEntry.calculation_sheet_id == sheet_id)
        .all()
    )
    return [
        {
            "section_number": row.section_number,
            "estimated_quantity": row.estimated_quantity,
            "quantity_submitted": row.quantity_submitted,
            "submission_breakdown": copy.deepcopy(row.submission_breakdown),
            "unit_price": row.unit_price,
        }
        for row in rows
    ]


def diff_transferred_sections(
    db: Session,
    calculation_sheet_no: str,
    previous_calculation_sheet_no: str,
    before_entries: Iterable,
    after_entries: Iterable,
) -> list[dict]:
    """Quantity and price changes for non-BOQ sections already sent to a sub-project.

    A section that was not on this sheet before the update is included when it
    belongs to a transferred item. A section removed from the sheet is a
    quantity change only; the price prompt is for a price that is still on the sheet.
    """
    before = _section_states(before_entries)
    after = _section_states(after_entries)
    sections = set(before) | set(after)
    if not sections:
        return []

    moved = {
        item.section_number: item.moved_to_project_id
        for item in db.query(models.NonBoqItem)
        .filter(models.NonBoqItem.section_number.in_(sections))
        .all()
        if item.moved_to_project_id
    }
    if not moved:
        return []

    sheet_no = _normalize(calculation_sheet_no)
    previous_no = _normalize(previous_calculation_sheet_no) or sheet_no
    changes = []
    for section, project_id in sorted(moved.items()):
        if section not in sections:
            continue
        project = project_registry.get_project(project_id)
        if project is None:
            continue
        old = before.get(section)
        new = after.get(section)
        old_estimated = old["estimated"] if old else 0.0
        new_estimated = new["estimated"] if new else 0.0
        old_submitted = old["submitted"] if old else 0.0
        new_submitted = new["submitted"] if new else 0.0
        old_breakdown = _breakdown_fingerprint(old["breakdowns"] if old else [])
        new_breakdown = _breakdown_fingerprint(new["breakdowns"] if new else [])
        details_changed = new is not None and old_breakdown != new_breakdown
        quantity_changed = (
            old_estimated != new_estimated
            or old_submitted != new_submitted
            or old_breakdown != new_breakdown
        )
        old_price = old["price"] if old else None
        new_price = new["price"] if new else None
        price_changed = new is not None and old_price != new_price
        if not quantity_changed and not price_changed:
            continue
        changes.append(
            {
                "project_id": project_id,
                "project_name": project.get("name") or project_id,
                "calculation_sheet_no": sheet_no,
                "previous_calculation_sheet_no": previous_no,
                "section_number": section,
                "quantity_changed": quantity_changed,
                "price_changed": price_changed,
                "old_estimated_quantity": old_estimated,
                "new_estimated_quantity": new_estimated,
                "old_quantity_submitted": old_submitted,
                "new_quantity_submitted": new_submitted,
                "old_price": old_price,
                "new_price": new_price,
                "details_changed": details_changed,
            }
        )
    return changes


def note_transferred_changes(
    db: Session,
    calculation_sheet_no: str,
    previous_calculation_sheet_no: str,
    before_entries: Iterable,
    after_entries: Iterable,
    updates: Optional[list],
) -> None:
    if updates is None:
        return
    updates.extend(
        diff_transferred_sections(
            db,
            calculation_sheet_no,
            previous_calculation_sheet_no,
            before_entries,
            after_entries,
        )
    )


def _open_project(project_id: str) -> Session:
    from database.database import get_project_engine, init_project_database

    init_project_database(project_id)
    return sessionmaker(bind=get_project_engine(project_id))()


def _find_sheet(db: Session, *numbers: str) -> Optional[models.CalculationSheet]:
    seen = set()
    for number in numbers:
        text = _normalize(number)
        if not text or text in seen:
            continue
        seen.add(text)
        sheet = (
            db.query(models.CalculationSheet)
            .filter(models.CalculationSheet.calculation_sheet_no == text)
            .first()
        )
        if sheet is not None:
            return sheet
    return None


def _source_entries(source: Session, sheet_no: str, section: str) -> list:
    return (
        source.query(models.CalculationEntry)
        .join(
            models.CalculationSheet,
            models.CalculationEntry.calculation_sheet_id == models.CalculationSheet.id,
        )
        .filter(
            models.CalculationSheet.calculation_sheet_no == sheet_no,
            models.CalculationEntry.section_number == section,
        )
        .order_by(models.CalculationEntry.id.asc())
        .all()
    )


def _first_price(entries: Iterable) -> float:
    for entry in entries:
        money = _money(_read(entry, "unit_price"))
        if money is not None:
            return money
    return 0.0


def _target_entries(db: Session, sheet_id: int, section: str) -> list:
    return (
        db.query(models.CalculationEntry)
        .filter(
            models.CalculationEntry.calculation_sheet_id == sheet_id,
            models.CalculationEntry.section_number == section,
        )
        .order_by(models.CalculationEntry.id.asc())
        .all()
    )


def _write_quantity(target_entry, source_entry) -> None:
    target_entry.estimated_quantity = source_entry.estimated_quantity
    target_entry.quantity_submitted = source_entry.quantity_submitted
    target_entry.submission_breakdown = copy.deepcopy(source_entry.submission_breakdown)
    target_entry.current_invoice_id = source_entry.current_invoice_id
    target_entry.invoice_description = source_entry.invoice_description


def _clone_entry(sheet_id: int, source_entry, unit_price) -> models.CalculationEntry:
    return models.CalculationEntry(
        calculation_sheet_id=sheet_id,
        section_number=source_entry.section_number,
        current_invoice_id=source_entry.current_invoice_id,
        invoice_description=source_entry.invoice_description,
        item_description=source_entry.item_description,
        estimated_quantity=source_entry.estimated_quantity,
        quantity_submitted=source_entry.quantity_submitted,
        submission_breakdown=copy.deepcopy(source_entry.submission_breakdown),
        notes=source_entry.notes,
        unit_price=unit_price,
        unit=source_entry.unit,
        system=source_entry.system,
    )


def _apply_section(
    target: Session,
    sheet: models.CalculationSheet,
    source_entries: list,
    section: str,
    update_quantity: bool,
    update_price: bool,
) -> None:
    current = _target_entries(target, sheet.id, section)
    preserved_price = current[0].unit_price if current else None
    source_price = _first_price(source_entries)

    if update_quantity and not source_entries:
        for entry in current:
            target.delete(entry)
        target.flush()
    elif update_quantity and len(source_entries) == len(current) and current:
        for target_entry, source_entry in zip(current, source_entries):
            _write_quantity(target_entry, source_entry)
            if update_price:
                target_entry.unit_price = source_entry.unit_price
        target.flush()
    elif update_quantity:
        for entry in current:
            target.delete(entry)
        target.flush()
        for source_entry in source_entries:
            price = source_entry.unit_price if update_price else preserved_price
            if price is None and not update_price:
                price = source_entry.unit_price
            target.add(_clone_entry(sheet.id, source_entry, price))
        target.flush()
    elif update_price and current:
        for entry in current:
            entry.unit_price = source_price
        target.flush()
    elif update_price and source_entries:
        for source_entry in source_entries:
            target.add(_clone_entry(sheet.id, source_entry, source_entry.unit_price))
        target.flush()

    if update_price:
        item = (
            target.query(models.BOQItem)
            .filter(models.BOQItem.section_number == section)
            .first()
        )
        if item is not None:
            item.price = source_price
            item.submitted_price = source_price


def apply_subproject_calc_updates(source: Session, choices: Iterable[dict]) -> dict:
    """Copy the confirmed quantity and price onto the sub-project sheet and BOQ row."""
    grouped: dict[str, list[dict]] = {}
    for choice in choices:
        if not choice.get("update_quantity") and not choice.get("update_price"):
            continue
        project_id = _normalize(choice.get("project_id"))
        section = _normalize(choice.get("section_number"))
        sheet_no = _normalize(choice.get("calculation_sheet_no"))
        if not project_id or not section or not sheet_no:
            continue
        grouped.setdefault(project_id, []).append(choice)

    updated = 0
    errors: list[str] = []
    for project_id, project_choices in grouped.items():
        project = project_registry.get_project(project_id)
        project_name = (project or {}).get("name") or project_id
        if project is None:
            errors.append(f"Project {project_name} was not found.")
            continue
        target = _open_project(project_id)
        try:
            sheets_to_push: dict[int, models.CalculationSheet] = {}
            applied = 0
            for choice in project_choices:
                section = _normalize(choice.get("section_number"))
                sheet_no = _normalize(choice.get("calculation_sheet_no"))
                previous_no = _normalize(choice.get("previous_calculation_sheet_no"))
                sheet = _find_sheet(target, previous_no, sheet_no)
                if sheet is None:
                    errors.append(
                        f"{sheet_no} / {section} was not found in {project_name}."
                    )
                    continue
                source_entries = _source_entries(source, sheet_no, section)
                _apply_section(
                    target,
                    sheet,
                    source_entries,
                    section,
                    bool(choice.get("update_quantity")),
                    bool(choice.get("update_price")),
                )
                sheets_to_push[sheet.id] = sheet
                applied += 1
            target.flush()
            for sheet in sheets_to_push.values():
                push_calculation_sheet_to_concentration_entries(target, sheet)
            target.commit()
            updated += applied
        except Exception as exc:
            target.rollback()
            logger.exception("Could not update project %s", project_id)
            errors.append(f"{project_name}: {exc}")
        finally:
            target.close()

    if updated and not errors:
        message = f"Updated {updated} item(s) in the sub-project."
    elif updated:
        message = f"Updated {updated} item(s) in the sub-project. " + " ".join(errors)
    elif errors:
        message = " ".join(errors)
    else:
        message = "Nothing was updated in the sub-project."
    return {"success": updated > 0 and not errors, "updated": updated, "errors": errors, "message": message}


def find_subproject_sheet_copies(
    source: Session,
    source_project_id: str,
    sheet_numbers: Iterable[str],
) -> list[dict]:
    """Calculation sheets with these numbers inside this project's sub-projects."""
    numbers = {_normalize(number) for number in sheet_numbers if _normalize(number)}
    if not numbers:
        return []
    copies = []
    for project_id in linked_project_ids(source, source_project_id):
        project = project_registry.get_project(project_id)
        if project is None:
            continue
        try:
            target = _open_project(project_id)
        except Exception:
            logger.exception("Could not open project %s", project_id)
            continue
        try:
            sheets = (
                target.query(models.CalculationSheet)
                .filter(models.CalculationSheet.calculation_sheet_no.in_(numbers))
                .order_by(models.CalculationSheet.calculation_sheet_no.asc())
                .all()
            )
            for sheet in sheets:
                copies.append(
                    {
                        "project_id": project_id,
                        "project_name": project.get("name") or project_id,
                        "calculation_sheet_no": sheet.calculation_sheet_no,
                    }
                )
        finally:
            target.close()
    return copies


def delete_sheets_from_subprojects(
    source: Session,
    source_project_id: str,
    sheet_numbers: Iterable[str],
) -> dict:
    """Delete matching calculation sheets from linked sub-projects."""
    copies = find_subproject_sheet_copies(source, source_project_id, sheet_numbers)
    by_project: dict[str, set[str]] = {}
    for copy in copies:
        by_project.setdefault(copy["project_id"], set()).add(copy["calculation_sheet_no"])

    deleted = 0
    errors: list[str] = []
    for project_id, numbers in by_project.items():
        project = project_registry.get_project(project_id)
        project_name = (project or {}).get("name") or project_id
        target = _open_project(project_id)
        try:
            sync = SyncService(target)
            for number in sorted(numbers):
                sheet = _find_sheet(target, number)
                if sheet is None:
                    continue
                sync.sync_calculation_sheet_deletion(sheet.id)
                sheet = _find_sheet(target, number)
                if sheet is not None:
                    target.delete(sheet)
                    deleted += 1
            target.commit()
        except Exception as exc:
            target.rollback()
            logger.exception("Could not delete sheets from %s", project_id)
            errors.append(f"{project_name}: {exc}")
        finally:
            target.close()

    if deleted and not errors:
        message = f"Deleted {deleted} calculation sheet(s) from the sub-project."
    elif errors:
        message = " ".join(errors)
    else:
        message = "No matching calculation sheet was found in a sub-project."
    return {
        "deleted": deleted,
        "errors": errors,
        "copies": copies,
        "message": message,
    }
