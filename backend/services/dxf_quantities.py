"""Lengths and unit counts from an AutoCAD DXF plan.

DWG is AutoCAD's own format. This reader takes DXF, the format AutoCAD saves
for other programs. A DWG file has to be saved as DXF first.
"""

import math
from pathlib import Path
from typing import List, Tuple


def _pairs(text: str) -> List[Tuple[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip() != ""]
    return [(lines[i], lines[i + 1]) for i in range(0, len(lines) - 1, 2)]


def _distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def quantities_from_dxf_text(text: str) -> dict:
    pairs = _pairs(text)
    in_entities = False
    entity = None
    start = None
    end = None
    vertices: List[Tuple[float, float]] = []
    pending_x = None
    closed = False
    length = 0.0
    line_count = 0
    unit_count = 0

    def finish():
        nonlocal length, line_count, unit_count, entity, start, end, vertices, pending_x, closed
        if entity == "LINE" and start and end:
            length += _distance(start, end)
            line_count += 1
        elif entity == "LWPOLYLINE" and len(vertices) >= 2:
            total = 0.0
            for index in range(len(vertices) - 1):
                total += _distance(vertices[index], vertices[index + 1])
            if closed and len(vertices) > 2:
                total += _distance(vertices[-1], vertices[0])
            length += total
            line_count += 1
        elif entity == "INSERT":
            unit_count += 1
        entity = None
        start = None
        end = None
        vertices = []
        pending_x = None
        closed = False

    for code, value in pairs:
        if code == "0" and value == "SECTION":
            continue
        if code == "2" and value == "ENTITIES":
            in_entities = True
            continue
        if code == "0" and value == "ENDSEC":
            if in_entities:
                finish()
            in_entities = False
            continue
        if not in_entities:
            continue
        if code == "0":
            finish()
            entity = value
            continue
        if entity == "LINE":
            if code == "10":
                start = (float(value), start[1] if start else 0.0)
            elif code == "20" and start:
                start = (start[0], float(value))
            elif code == "11":
                end = (float(value), end[1] if end else 0.0)
            elif code == "21" and end:
                end = (end[0], float(value))
        elif entity == "LWPOLYLINE":
            if code == "70":
                closed = int(float(value)) & 1 == 1
            elif code == "10":
                pending_x = float(value)
            elif code == "20" and pending_x is not None:
                vertices.append((pending_x, float(value)))
                pending_x = None
    finish()
    return {
        "length": round(length, 3),
        "line_count": line_count,
        "unit_count": unit_count,
        "readable": True,
    }


def measure_plan(path: Path) -> dict:
    suffix = path.suffix.lower()
    if suffix == ".dwg":
        return {
            "length": 0.0,
            "line_count": 0,
            "unit_count": 0,
            "readable": False,
            "detail": "Save the AutoCAD drawing as DXF. DWG itself is not read.",
        }
    if suffix != ".dxf":
        return {
            "length": 0.0,
            "line_count": 0,
            "unit_count": 0,
            "readable": False,
            "detail": "Only DXF plans can be measured.",
        }
    if not path.is_file():
        return {
            "length": 0.0,
            "line_count": 0,
            "unit_count": 0,
            "readable": False,
            "detail": "Plan file was not found.",
        }
    text = path.read_text(encoding="utf-8", errors="ignore")
    result = quantities_from_dxf_text(text)
    result["detail"] = "Measured from DXF."
    return result
