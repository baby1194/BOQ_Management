"""Track calculation-sheet section numbers that are not in the BOQ list."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from database import project_registry
from models import models


def get_calculation_sheet_nos_by_section(
    db: Session,
    section_numbers: Iterable[str],
) -> dict[str, list[str]]:
    """Map section numbers to distinct calculation sheet numbers from calc entries."""
    normalized = {
        n for n in (_normalize_section_number(s) for s in section_numbers) if n
    }
    if not normalized:
        return {}

    rows = (
        db.query(
            models.CalculationEntry.section_number,
            models.CalculationSheet.calculation_sheet_no,
        )
        .join(
            models.CalculationSheet,
            models.CalculationEntry.calculation_sheet_id == models.CalculationSheet.id,
        )
        .filter(models.CalculationEntry.section_number.in_(normalized))
        .order_by(models.CalculationSheet.calculation_sheet_no.asc())
        .all()
    )

    result: dict[str, set[str]] = {section: set() for section in normalized}
    for section_number, calc_sheet_no in rows:
        key = _normalize_section_number(section_number)
        if key and calc_sheet_no:
            result.setdefault(key, set()).add(str(calc_sheet_no).strip())

    return {key: sorted(values) for key, values in result.items()}


def _stored_sheet_nos(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def delete_section_from_database(db: Session, section_number: str) -> bool:
    """Drop one section from a project: BOQ row, concentration sheet, and calc rows."""
    section = _normalize_section_number(section_number)
    if not section:
        return False

    found = False
    entries = (
        db.query(models.CalculationEntry)
        .filter(models.CalculationEntry.section_number == section)
        .all()
    )
    sheet_ids = {entry.calculation_sheet_id for entry in entries}
    for entry in entries:
        db.delete(entry)
        found = True
    db.flush()

    for sheet_id in sheet_ids:
        remaining = (
            db.query(models.CalculationEntry)
            .filter(models.CalculationEntry.calculation_sheet_id == sheet_id)
            .count()
        )
        if remaining == 0:
            sheet = (
                db.query(models.CalculationSheet)
                .filter(models.CalculationSheet.id == sheet_id)
                .first()
            )
            if sheet is not None:
                db.delete(sheet)

    item = (
        db.query(models.BOQItem)
        .filter(models.BOQItem.section_number == section)
        .first()
    )
    if item is not None:
        found = True
        for sheet in (
            db.query(models.ConcentrationSheet)
            .filter(models.ConcentrationSheet.boq_item_id == item.id)
            .all()
        ):
            db.delete(sheet)
        db.delete(item)
    db.flush()
    return found


def delete_section_from_linked_project(project_id: str, section_number: str) -> bool:
    """Remove a section from the sub-project it was copied into."""
    if not project_id or project_registry.get_project(project_id) is None:
        return False
    from sqlalchemy.orm import sessionmaker

    from database.database import get_project_engine, init_project_database

    init_project_database(project_id)
    Target = sessionmaker(bind=get_project_engine(project_id))
    target = Target()
    try:
        deleted = delete_section_from_database(target, section_number)
        target.commit()
        return deleted
    except Exception:
        target.rollback()
        logger.exception(
            "Could not remove %s from project %s", section_number, project_id
        )
        return False
    finally:
        target.close()


def reconcile_missing_non_boq_items(db: Session) -> tuple[list[str], bool]:
    """Mark non-BOQ sections that are no longer on any calculation sheet.

    A section that was copied into a sub-project is removed from that project.
    Sections that show up on a sheet again are cleared back to a normal row.
    Returns notice sentences and whether any row changed.
    """
    items = db.query(models.NonBoqItem).all()
    if not items:
        return [], False

    live = get_calculation_sheet_nos_by_section(
        db, [item.section_number for item in items]
    )
    project_names = {
        project["id"]: project["name"] for project in project_registry.list_projects()
    }
    notices: list[str] = []
    changed = False
    now = datetime.now(timezone.utc)

    for item in items:
        sheets = live.get(item.section_number) or []
        if sheets:
            joined = ", ".join(sheets)
            if item.source_sheet_nos != joined:
                item.source_sheet_nos = joined
                changed = True
            if item.removed_at is not None:
                item.removed_at = None
                item.removed_from_project = False
                item.moved_to_project_id = None
                item.moved_at = None
                changed = True
            continue

        if item.removed_at is None:
            item.removed_at = now
            changed = True
            project_name = project_names.get(item.moved_to_project_id or "", "")
            if item.moved_to_project_id and not item.removed_from_project:
                removed = delete_section_from_linked_project(
                    item.moved_to_project_id, item.section_number
                )
                project_missing = project_registry.get_project(item.moved_to_project_id) is None
                if removed or project_missing:
                    item.removed_from_project = True
                    label = project_name or item.moved_to_project_id
                    notices.append(
                        f"{item.section_number} was deleted from the calculation sheets "
                        f"and removed from project {label}."
                    )
                else:
                    label = project_name or item.moved_to_project_id
                    notices.append(
                        f"{item.section_number} was deleted from the calculation sheets. "
                        f"It could not be removed from project {label}."
                    )
            else:
                notices.append(
                    f"{item.section_number} was deleted from the calculation sheets."
                )
            continue

        if item.moved_to_project_id and not item.removed_from_project:
            removed = delete_section_from_linked_project(
                item.moved_to_project_id, item.section_number
            )
            project_missing = project_registry.get_project(item.moved_to_project_id) is None
            if removed or project_missing:
                item.removed_from_project = True
                changed = True
                label = project_names.get(item.moved_to_project_id, item.moved_to_project_id)
                notices.append(
                    f"{item.section_number} was removed from project {label}."
                )

    return notices, changed


def build_non_boq_export_rows(items: Iterable[Dict]) -> list[dict]:
    """Flatten non-BOQ items into export rows with No, item_no, and calc_sheet_no."""
    rows: list[dict] = []
    row_no = 1
    for item in items:
        section_number = item.get("section_number", "")
        sheet_nos = item.get("calculation_sheet_nos") or []
        if not sheet_nos:
            rows.append(
                {
                    "no": row_no,
                    "item_no": section_number,
                    "calc_sheet_no": "",
                }
            )
            row_no += 1
            continue
        for calc_sheet_no in sheet_nos:
            rows.append(
                {
                    "no": row_no,
                    "item_no": section_number,
                    "calc_sheet_no": calc_sheet_no,
                }
            )
            row_no += 1
    return rows


def build_non_boq_import_rows(records: List[dict]) -> list[dict]:
    """One BOQ row per section. Quantity is the sum of calculated amounts. Price is the first cell found."""
    grouped: dict[str, dict] = {}
    for record in records:
        section = _normalize_section_number(record.get("section_number"))
        if not section:
            continue
        row = grouped.setdefault(
            section,
            {
                "section_number": section,
                "description": "",
                "unit": "יח'",
                "quantity": 0.0,
                "quantity_submitted": 0.0,
                "price": 0.0,
                "system": "",
            },
        )
        description = (record.get("description") or "").strip()
        if description and not row["description"]:
            row["description"] = description
        system = (record.get("system") or "").strip()
        if system and not row["system"]:
            row["system"] = system
        row["quantity"] += float(record.get("estimated_quantity") or 0)
        row["quantity_submitted"] += float(record.get("quantity_submitted") or 0)
        price = record.get("unit_price")
        if row["price"] == 0.0 and price not in (None, "", 0, 0.0):
            row["price"] = float(price)
    rows = []
    for section in sorted(grouped):
        row = grouped[section]
        quantity = round(row["quantity"], 3)
        price = round(float(row["price"] or 0), 2)
        if not row["description"]:
            row["description"] = section
        rows.append(
            {
                "section_number": section,
                "description": row["description"],
                "unit": row["unit"],
                "quantity": quantity,
                "quantity_submitted": round(row["quantity_submitted"], 3),
                "price": price,
                "system": row["system"],
                "total": round(quantity * price, 2),
                "missing_price": price == 0.0,
            }
        )
    return rows


def _item_descriptions_from_workbook(path: str) -> dict[str, str]:
    """Section number to Excel row 22 text. Empty when the file cannot be read."""
    try:
        from services.excel_service import ExcelService

        sheet_data = ExcelService().read_calculation_sheet_data(path)
    except Exception as exc:
        logger.warning("Could not read item descriptions from %s: %s", path, exc)
        return {}

    descriptions: dict[str, str] = {}
    for entry in sheet_data.get("entries") or []:
        section = _normalize_section_number(entry.get("section_number"))
        text = (entry.get("item_description") or "").strip()
        if section and text and section not in descriptions:
            descriptions[section] = text
    return descriptions


def backfill_item_descriptions(db: Session) -> int:
    """Store Excel row 22 on entries that were imported before that cell was kept."""
    sections = {
        item.section_number
        for item in db.query(models.NonBoqItem).all()
    }
    if not sections:
        return 0

    rows = (
        db.query(models.CalculationEntry, models.CalculationSheet)
        .join(
            models.CalculationSheet,
            models.CalculationEntry.calculation_sheet_id == models.CalculationSheet.id,
        )
        .filter(models.CalculationEntry.section_number.in_(sections))
        .all()
    )
    missing = [
        (entry, sheet)
        for entry, sheet in rows
        if not (entry.item_description or "").strip() and sheet.source_file_path
    ]
    if not missing:
        return 0

    by_path: dict[str, dict[str, str]] = {}
    updated = 0
    for entry, sheet in missing:
        path = sheet.source_file_path
        if path not in by_path:
            by_path[path] = _item_descriptions_from_workbook(path)
        section = _normalize_section_number(entry.section_number)
        text = by_path[path].get(section or "", "")
        if text:
            entry.item_description = text
            updated += 1
    if updated:
        db.commit()
    return updated


def non_boq_import_rows(db: Session) -> list[dict]:
    """Calculated quantity, description, and price for every non-BOQ section."""
    backfill_item_descriptions(db)
    sections = {
        item.section_number
        for item in db.query(models.NonBoqItem).all()
    }
    if not sections:
        return []
    entries = (
        db.query(models.CalculationEntry, models.CalculationSheet)
        .join(
            models.CalculationSheet,
            models.CalculationEntry.calculation_sheet_id == models.CalculationSheet.id,
        )
        .filter(models.CalculationEntry.section_number.in_(sections))
        .order_by(
            models.CalculationSheet.calculation_sheet_no.asc(),
            models.CalculationEntry.id.asc(),
        )
        .all()
    )
    records = []
    for entry, _sheet in entries:
        records.append(
            {
                "section_number": entry.section_number,
                "description": (entry.item_description or "").strip(),
                "estimated_quantity": entry.estimated_quantity,
                "quantity_submitted": entry.quantity_submitted,
                "unit_price": entry.unit_price,
                "system": entry.system,
            }
        )
    return build_non_boq_import_rows(records)


def list_non_boq_items_with_calc_sheets(db: Session) -> list[dict]:
    """Return non-BOQ items enriched with related calculation sheet numbers."""
    items = (
        db.query(models.NonBoqItem)
        .order_by(models.NonBoqItem.section_number.asc())
        .all()
    )
    sheet_nos_by_section = get_calculation_sheet_nos_by_section(
        db,
        [item.section_number for item in items],
    )
    priced = {row["section_number"]: row for row in non_boq_import_rows(db)}
    project_names = {
        project["id"]: project["name"] for project in project_registry.list_projects()
    }
    return [
        {
            "id": item.id,
            "section_number": item.section_number,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "description": priced.get(item.section_number, {}).get("description") or "",
            "unit": priced.get(item.section_number, {}).get("unit") or "יח'",
            "quantity": priced.get(item.section_number, {}).get("quantity") or 0.0,
            "quantity_submitted": priced.get(item.section_number, {}).get("quantity_submitted") or 0.0,
            "price": priced.get(item.section_number, {}).get("price") or 0.0,
            "system": priced.get(item.section_number, {}).get("system") or "",
            "calculation_sheet_nos": (
                sheet_nos_by_section.get(item.section_number, [])
                or _stored_sheet_nos(item.source_sheet_nos)
            ),
            "moved_to_project_id": item.moved_to_project_id,
            "moved_to_project_name": project_names.get(item.moved_to_project_id or ""),
            "moved_at": item.moved_at,
            "removed_at": item.removed_at,
            "removed_from_project": bool(item.removed_from_project),
        }
        for item in items
    ]


def select_import_rows(rows: List[dict], section_numbers: Optional[Iterable[str]]) -> list[dict]:
    """All rows when nothing is chosen; otherwise only the chosen sections."""
    if section_numbers is None:
        return list(rows)
    chosen = {n for n in (_normalize_section_number(s) for s in section_numbers) if n}
    return [row for row in rows if row["section_number"] in chosen]


def mark_non_boq_items_moved(db: Session, section_numbers: Iterable[str], project_id: str) -> int:
    sections = list(section_numbers)
    if not sections:
        return 0
    now = datetime.now(timezone.utc)
    items = (
        db.query(models.NonBoqItem)
        .filter(models.NonBoqItem.section_number.in_(sections))
        .all()
    )
    for item in items:
        item.moved_to_project_id = project_id
        item.moved_at = now
    return len(items)

logger = logging.getLogger(__name__)


def _normalize_section_number(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def register_non_boq_items_from_calculation_entries(
    db: Session,
    entries: Iterable[Dict],
) -> int:
    """
    Add section numbers from calc sheet entries that are not in the BOQ list.
    Returns the number of newly registered items.
    """
    section_numbers: set[str] = set()
    for entry in entries:
        section_number = _normalize_section_number(entry.get("section_number"))
        if section_number:
            section_numbers.add(section_number)

    if not section_numbers:
        return 0

    existing_boq = {
        row[0]
        for row in db.query(models.BOQItem.section_number)
        .filter(models.BOQItem.section_number.in_(section_numbers))
        .all()
    }
    missing_from_boq = section_numbers - existing_boq
    if not missing_from_boq:
        return 0

    existing_non_boq = {
        row[0]
        for row in db.query(models.NonBoqItem.section_number)
        .filter(models.NonBoqItem.section_number.in_(missing_from_boq))
        .all()
    }

    added = 0
    for section_number in sorted(missing_from_boq):
        if section_number in existing_non_boq:
            continue
        db.add(models.NonBoqItem(section_number=section_number))
        added += 1

    if added:
        logger.info("Registered %s new non-BOQ item(s): %s", added, sorted(missing_from_boq))
    return added


def remove_non_boq_item_by_section(db: Session, section_number: str) -> bool:
    """Remove a section from the non-BOQ list (e.g. after adding to BOQ)."""
    normalized = _normalize_section_number(section_number)
    if not normalized:
        return False

    deleted = (
        db.query(models.NonBoqItem)
        .filter(models.NonBoqItem.section_number == normalized)
        .delete()
    )
    return deleted > 0
