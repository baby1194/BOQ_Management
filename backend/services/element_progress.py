"""Which contract items for one concrete element have been submitted."""

from typing import Iterable, List


def _blob(*parts) -> str:
    return " ".join(str(part) for part in parts if part).casefold()


def items_for_element(
    element: str,
    boq_items: Iterable[dict],
    entries_by_section: dict,
    drawing_names: Iterable[str] = (),
) -> List[dict]:
    needle = (element or "").strip().casefold()
    if not needle:
        return []
    names = [name.casefold() for name in drawing_names if name and str(name).strip()]
    rows = []
    for item in boq_items:
        section = item.get("section_number") or ""
        entries = entries_by_section.get(section, [])
        texts = [_blob(item.get("description"))]
        for entry in entries:
            texts.append(
                _blob(
                    entry.get("description"),
                    entry.get("invoice_description"),
                    entry.get("drawing_no"),
                    entry.get("section_number"),
                )
            )
        haystack = " ".join(texts)
        linked = needle in haystack or any(name in haystack for name in names)
        if not linked:
            continue
        submitted = float(item.get("quantity_submitted") or 0)
        rows.append(
            {
                "section_number": section,
                "description": item.get("description") or "",
                "contract_quantity": float(item.get("contract_quantity") or 0),
                "quantity_submitted": submitted,
                "submitted": submitted > 0,
            }
        )
    rows.sort(key=lambda row: (not row["submitted"], row["section_number"]))
    return rows
