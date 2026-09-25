"""Items whose submitted quantity has passed the contract quantity."""

from typing import Dict, Iterable, Optional


def _invoice_sort_key(invoice: str):
    text = str(invoice).strip()
    try:
        return (0, int(text), text)
    except ValueError:
        return (1, 0, text)


def first_invoice_over_contract(
    period_qty: Dict[str, float], contract_qty: float
) -> Optional[str]:
    """First invoice, in invoice order, where the running submitted total exceeds the contract."""
    running = 0.0
    limit = float(contract_qty or 0)
    for invoice in sorted(period_qty, key=_invoice_sort_key):
        running += float(period_qty[invoice] or 0)
        if running > limit + 1e-9:
            return str(invoice)
    return None


def period_quantities(entries: Iterable) -> Dict[str, float]:
    """Sum submitted quantity per invoice across concentration entries."""
    totals: Dict[str, float] = {}
    for entry in entries:
        breakdown = getattr(entry, "submission_breakdown", None) or {}
        if not isinstance(breakdown, dict):
            breakdown = {}
        periods = breakdown.get("periods") or {}
        if periods:
            for invoice, qty in periods.items():
                key = str(invoice)
                totals[key] = totals.get(key, 0.0) + float(qty or 0)
            continue
        invoice = getattr(entry, "drawing_no", None) or breakdown.get("current_drawing_no")
        if invoice:
            key = str(invoice)
            totals[key] = totals.get(key, 0.0) + float(
                getattr(entry, "quantity_submitted", 0) or 0
            )
    return totals


def rows_over_contract(db, rows):
    """Keep rows whose submitted quantity exceeds the current contract quantity.

    Adds overrun_invoice_no: the invoice where the running submitted total first crossed.
    """
    from models import models

    items = {item.id: item for item in db.query(models.BOQItem).all()}
    updates_by_item = {}
    for update in db.query(models.BOQItemQuantityUpdate).all():
        updates_by_item.setdefault(update.boq_item_id, []).append(update)

    entries_by_section = {}
    for entry in db.query(models.ConcentrationEntry).all():
        entries_by_section.setdefault(entry.section_number, []).append(entry)

    kept = []
    for row in rows:
        item = items.get(row.get("boq_item_id"))
        if item is None:
            section = row.get("section_number")
            item = next((candidate for candidate in items.values() if candidate.section_number == section), None)
        if item is None:
            continue
        contract_qty = current_contract_quantity(item, updates_by_item.get(item.id, []))
        submitted = float(item.quantity_submitted or 0)
        if submitted <= contract_qty + 1e-9:
            continue
        invoice = first_invoice_over_contract(
            period_quantities(entries_by_section.get(item.section_number, [])),
            contract_qty,
        )
        exported = dict(row)
        exported.pop("boq_item_id", None)
        exported["overrun_invoice_no"] = invoice or ""
        kept.append(exported)
    return kept


def current_contract_quantity(item, quantity_updates) -> float:
    """Latest updated contract quantity, or the original when there is no update."""
    latest = None
    latest_index = -1
    for update in quantity_updates:
        contract_update = getattr(update, "contract_update", None)
        index = getattr(contract_update, "update_index", None)
        if index is None:
            continue
        if index >= latest_index:
            latest_index = index
            latest = update
    if latest is not None:
        return float(latest.updated_contract_quantity or 0)
    return float(getattr(item, "original_contract_quantity", 0) or 0)
