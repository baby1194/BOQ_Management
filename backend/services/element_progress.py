"""Which contract items for one concrete element have been submitted."""

import re
from typing import Iterable, List

_ELEMENT_CODE = re.compile(r"(?<![\w.])([A-Za-z]{1,5})\s?-\s?(\d{1,4}[A-Za-z]?)(?!\w)")
_SHORT_NAME = re.compile(r"^(?=.*[^\W\d_])(?=.*\d)[\w\- /]{2,20}$")
_DASH = re.compile(r"\s*-\s*")
_WORD_SPLIT = re.compile(r"[\n,;/|]+")


def _normalize(text) -> str:
    return _DASH.sub("-", str(text or "")).strip().casefold()


def element_names_in(text, whole_value: bool = False) -> List[str]:
    """Element codes such as DC-36 inside a description. whole_value also accepts a short name like 'Wall 4'."""
    value = str(text or "").strip()
    names = [f"{letters.upper()}-{number.upper()}" for letters, number in _ELEMENT_CODE.findall(value)]
    if not names and whole_value and _SHORT_NAME.match(value) and not re.fullmatch(r"[\d.\-/ ]+", value):
        names.append(_DASH.sub("-", value))
    return names


def element_names_from_entries(entries: Iterable[dict]) -> List[str]:
    """Names found in concentration Description and Work Description."""
    found = {}
    for entry in entries:
        names = element_names_in(entry.get("description"), whole_value=True)
        names += element_names_in(entry.get("invoice_description"))
        for name in names:
            found.setdefault(name.casefold(), name)
    return sorted(found.values(), key=str.casefold)


def split_search_words(text: str) -> List[str]:
    """Words typed as RW-18 / DC-50 / rails, in the order they were written."""
    words = []
    seen = set()
    for part in _WORD_SPLIT.split(str(text or "")):
        word = part.strip()
        key = _normalize(word)
        if not key or key in seen:
            continue
        seen.add(key)
        words.append(word)
    return words


def mentions(text, element: str) -> bool:
    needle = _normalize(element)
    if not needle:
        return False
    return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", _normalize(text)) is not None


def items_for_element(
    element: str,
    boq_items: Iterable[dict],
    entries_by_section: dict,
    drawing_names: Iterable[str] = (),
) -> List[dict]:
    """Contract items tied to the element, with the quantities of the rows that name it."""
    if not (element or "").strip():
        return []
    names = [element] + [name for name in drawing_names if name and str(name).strip()]

    def linked(text) -> bool:
        return any(mentions(text, name) for name in names)

    rows = []
    for item in boq_items:
        section = item.get("section_number") or ""
        entries = [
            entry for entry in entries_by_section.get(section, [])
            if linked(entry.get("description"))
            or linked(entry.get("invoice_description"))
            or linked(entry.get("drawing_no"))
            or linked(entry.get("calculation_sheet_no"))
        ]
        if not entries and not linked(item.get("description")):
            continue
        if entries:
            estimated = sum(float(e.get("estimated_quantity") or 0) for e in entries)
            submitted = sum(float(e.get("quantity_submitted") or 0) for e in entries)
        else:
            estimated = float(item.get("estimated_quantity") or 0)
            submitted = float(item.get("quantity_submitted") or 0)
        rows.append(
            {
                "section_number": section,
                "description": item.get("description") or "",
                "contract_quantity": float(item.get("contract_quantity") or 0),
                "estimated_quantity": round(estimated, 3),
                "quantity_submitted": round(submitted, 3),
                "submitted": submitted > 0,
                "calculation_sheet_nos": sorted(
                    {str(e.get("calculation_sheet_no")) for e in entries if e.get("calculation_sheet_no")}
                ),
            }
        )
    rows.sort(key=lambda row: (not row["submitted"], row["section_number"]))
    return rows


def rows_for_words(
    text: str,
    boq_items: Iterable[dict],
    entries_by_section: dict,
    drawing_names_by_element: dict = None,
) -> List[dict]:
    """One row per word and connected section number. A word with no items stays visible."""
    drawing_names_by_element = drawing_names_by_element or {}
    boq_items = list(boq_items)
    table = []
    for word in split_search_words(text):
        names = drawing_names_by_element.get(_normalize(word), [])
        found = items_for_element(word, boq_items, entries_by_section, names)
        known = {row["section_number"] for row in found}
        needle = _normalize(word)
        for item in boq_items:
            section = item.get("section_number") or ""
            if section in known or needle not in _normalize(section):
                continue
            found.append(
                {
                    "section_number": section,
                    "description": item.get("description") or "",
                }
            )
            known.add(section)
        if not found:
            table.append({"word": word, "section_number": "", "description": ""})
            continue
        for row in found:
            table.append(
                {
                    "word": word,
                    "section_number": row["section_number"],
                    "description": row.get("description") or "",
                }
            )
    return table


def word_items_workbook(rows: List[dict], language: str = "en") -> bytes:
    from io import BytesIO

    from openpyxl import Workbook
    from openpyxl.styles import Font

    hebrew = language == "he"
    headers = (
        ["מילה", "מספר סעיף", "תיאור"]
        if hebrew
        else ["Word", "Section number", "Description"]
    )
    book = Workbook()
    sheet = book.active
    sheet.title = "Items"
    sheet.sheet_view.rightToLeft = hebrew
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        sheet.append([row["word"], row["section_number"], row["description"]])
    sheet.column_dimensions["A"].width = 22
    sheet.column_dimensions["B"].width = 22
    sheet.column_dimensions["C"].width = 60
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()
