"""Add a parent project's linked subprojects into its dashboard totals.

Exception items copied into a subproject keep a snapshot on the parent.
That snapshot is not the subproject's current estimate or submitted total.
The live BOQ sums on each linked project are the numbers to add.
"""

from __future__ import annotations

import logging
from typing import Iterable

from sqlalchemy import func
from sqlalchemy.orm import Session, sessionmaker

from database import project_registry
from models import models

logger = logging.getLogger(__name__)

EMPTY_TOTALS = {
    "project_ids": [],
    "boq_count": 0,
    "concentration_count": 0,
    "calculation_count": 0,
    "items_with_concentration": 0,
    "total_contract": 0.0,
    "total_estimate": 0.0,
    "total_submitted": 0.0,
    "total_internal": 0.0,
    "total_approved": 0.0,
    "estimated_qty": 0.0,
    "submitted_qty": 0.0,
    "approved_qty": 0.0,
}


def linked_project_ids(source: Session, source_project_id: str) -> list[str]:
    """Subprojects created from this project, plus any project that received its items."""
    moved = {
        project_id
        for (project_id,) in source.query(models.NonBoqItem.moved_to_project_id).all()
        if project_id and project_id != source_project_id
    }
    linked: list[str] = []
    for project in project_registry.list_projects():
        project_id = project["id"]
        if project_id == source_project_id:
            continue
        if project.get("source_project_id") == source_project_id or project_id in moved:
            linked.append(project_id)
    return linked


def _project_totals(db: Session) -> dict:
    money = db.query(
        func.count(models.BOQItem.id),
        func.coalesce(func.sum(models.BOQItem.total_contract_sum), 0.0),
        func.coalesce(func.sum(models.BOQItem.total_estimate), 0.0),
        func.coalesce(func.sum(models.BOQItem.total_submitted), 0.0),
        func.coalesce(func.sum(models.BOQItem.internal_total), 0.0),
        func.coalesce(func.sum(models.BOQItem.approved_signed_total), 0.0),
        func.coalesce(func.sum(models.BOQItem.estimated_quantity), 0.0),
        func.coalesce(func.sum(models.BOQItem.quantity_submitted), 0.0),
        func.coalesce(func.sum(models.BOQItem.approved_signed_quantity), 0.0),
    ).one()
    concentration_count = db.query(func.count(models.ConcentrationSheet.id)).scalar() or 0
    items_with_concentration = (
        db.query(func.count(func.distinct(models.ConcentrationSheet.boq_item_id))).scalar()
        or 0
    )
    calculation_count = db.query(func.count(models.CalculationSheet.id)).scalar() or 0
    return {
        "boq_count": int(money[0] or 0),
        "concentration_count": int(concentration_count),
        "calculation_count": int(calculation_count),
        "items_with_concentration": int(items_with_concentration),
        "total_contract": float(money[1] or 0),
        "total_estimate": float(money[2] or 0),
        "total_submitted": float(money[3] or 0),
        "total_internal": float(money[4] or 0),
        "total_approved": float(money[5] or 0),
        "estimated_qty": float(money[6] or 0),
        "submitted_qty": float(money[7] or 0),
        "approved_qty": float(money[8] or 0),
    }


def _open_project(project_id: str) -> Session:
    from database.database import get_project_engine, init_project_database

    init_project_database(project_id)
    return sessionmaker(bind=get_project_engine(project_id))()


def _add(totals: dict, part: dict) -> None:
    for key, value in part.items():
        totals[key] += value


def linked_subproject_totals(source: Session, source_project_id: str) -> dict:
    """Sums of every linked subproject. The parent project itself is not included."""
    totals = dict(EMPTY_TOTALS)
    totals["project_ids"] = []
    for project_id in linked_project_ids(source, source_project_id):
        child = None
        try:
            child = _open_project(project_id)
            _add(totals, _project_totals(child))
            totals["project_ids"].append(project_id)
        except Exception:
            logger.exception("Could not read totals for linked project %s", project_id)
        finally:
            if child is not None:
                child.close()
    return totals


def loose_exception_items(items: Iterable[dict], rolled_up_project_ids: Iterable[str]) -> list[dict]:
    """Non-BOQ rows that are not already counted inside a rolled-up subproject."""
    rolled = set(rolled_up_project_ids)
    kept = []
    for item in items:
        if item.get("removed_at"):
            continue
        moved_to = item.get("moved_to_project_id")
        if moved_to and moved_to in rolled:
            continue
        kept.append(item)
    return kept
