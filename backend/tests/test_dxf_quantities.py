from services.dxf_quantities import measure_plan, quantities_from_dxf_text


DXF = """
0
SECTION
2
ENTITIES
0
LINE
10
0
20
0
11
3
21
4
0
LWPOLYLINE
90
2
70
0
10
0
20
0
10
10
20
0
0
INSERT
2
BLOCK
0
ENDSEC
0
EOF
"""


def test_line_length_polyline_and_insert_count():
    result = quantities_from_dxf_text(DXF)
    assert result["length"] == 15.0
    assert result["line_count"] == 2
    assert result["unit_count"] == 1


def test_dwg_is_reported_as_not_readable(tmp_path):
    path = tmp_path / "plan.dwg"
    path.write_bytes(b"not a dxf")
    result = measure_plan(path)
    assert result["readable"] is False
    assert "DXF" in result["detail"]
