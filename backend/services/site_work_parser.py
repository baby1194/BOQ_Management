"""Turn site-report and WhatsApp text into a deduplicated list of site work."""

import re
import unicodedata
from typing import Iterable, List, Optional

# Contract systems named in the client notes, plus common Hebrew labels.
SYSTEM_ALIASES = [
    ("Lighting", ("lighting", "תאורה")),
    ("Demolition", ("demolition", "הריסה")),
    ("Drainage", ("drainage", "ניקוז")),
    ("Sewage", ("sewage", "sewer", "ביוב")),
    ("Concrete", ("concrete", "בטון")),
]

EXCEPTION_SYSTEM = "Exception"
EXCEPTION_MARKERS = ("exception", "exceptional", "חריג", "חריגה", "חריגים")
ADDITIONAL_MARKERS = (
    "additional work",
    "extra work",
    "עבודה נוספת",
    "עבודות נוספות",
)

_SKIP_LINE = re.compile(
    r"^(hi|hello|hey|thanks|thank you|ok|okay|שלום|תודה|היי|בוקר טוב)[.!? ]*$",
    re.IGNORECASE,
)


def normalize_key(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text).casefold()
    folded = re.sub(r"\s+", " ", folded).strip(" .;,-")
    return folded[:500]


def _split_lines(text: str) -> List[str]:
    chunks: List[str] = []
    for raw in re.split(r"[\r\n]+", text or ""):
        parts = re.split(r"[.;]+", raw)
        for part in parts:
            line = part.strip(" \t-•*")
            if line:
                chunks.append(line)
    return chunks


def _match_system(line: str, known_systems: Iterable[str]) -> Optional[str]:
    lowered = line.casefold()
    ranked = sorted((s for s in known_systems if s and s.strip()), key=len, reverse=True)
    for name in ranked:
        if name.casefold() in lowered:
            return name.strip()
    for canonical, aliases in SYSTEM_ALIASES:
        if any(alias.casefold() in lowered for alias in aliases):
            return canonical
    return None


def _classification(line: str, system_name: Optional[str]) -> Optional[str]:
    lowered = line.casefold()
    if any(marker.casefold() in lowered for marker in ADDITIONAL_MARKERS):
        return "additional_work"
    if any(marker.casefold() in lowered for marker in EXCEPTION_MARKERS):
        return "exception"
    if system_name:
        return "system"
    return None


CLASSIFICATIONS = ("system", "exception", "additional_work")
SOURCES = ("site_report", "whatsapp")


def manual_task(
    description: str,
    system_name: str,
    classification: str,
    source: str,
    work_date: Optional[str] = None,
) -> dict:
    text = (description or "").strip()
    if len(text) < 3:
        raise ValueError("Description is required")
    if classification not in CLASSIFICATIONS:
        raise ValueError("Classification is invalid")
    if source not in SOURCES:
        raise ValueError("Source is invalid")
    system = (system_name or "").strip() or EXCEPTION_SYSTEM
    date = (work_date or "").strip() or None
    return {
        "description": text,
        "dedupe_key": normalize_key(text),
        "system_name": system,
        "classification": classification,
        "source": source,
        "work_date": date,
    }


def classification_after_system_change(current: str, system_name: str) -> str:
    """Changing the system clears an uncategorized Exception, and keeps additional work."""
    if (system_name or "").strip().casefold() == EXCEPTION_SYSTEM.casefold():
        if current == "additional_work":
            return "additional_work"
        return "exception"
    if current == "exception":
        return "system"
    return current


def parse_work_lines(text: str, known_systems: Optional[Iterable[str]] = None) -> List[dict]:
    """Keep work lines only, and collapse the same task inside one ingest."""
    systems = list(known_systems or [])
    seen = set()
    items: List[dict] = []
    for line in _split_lines(text):
        if len(line) < 3 or _SKIP_LINE.match(line):
            continue
        system_name = _match_system(line, systems)
        classification = _classification(line, system_name)
        # A job that cannot be matched to a contract system stays on the list.
        if system_name is None:
            system_name = EXCEPTION_SYSTEM
        if classification is None:
            classification = "exception"
        key = normalize_key(line)
        if not key or key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "description": line,
                "dedupe_key": key,
                "system_name": system_name,
                "classification": classification,
            }
        )
    return items
