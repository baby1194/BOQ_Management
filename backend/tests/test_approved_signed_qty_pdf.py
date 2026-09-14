from datetime import datetime, timezone

from services.approved_signed_qty_pdf_service import parse_reporting_month_from_text


def test_parse_reporting_month_from_hebrew_label():
    text = 'חודש דיווח 30.06.2026 מספר החשבון 0000000084'
    parsed = parse_reporting_month_from_text(text)
    assert parsed == datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_parse_reporting_month_ignores_unrelated_dates():
    text = "תאריך הדפסה 01.07.2026\nחודש דיווח 30.06.2026"
    parsed = parse_reporting_month_from_text(text)
    assert parsed is not None
    assert parsed.month == 6
    assert parsed.year == 2026


def test_parse_reporting_month_english_label():
    parsed = parse_reporting_month_from_text("Reporting month: 15/04/2025")
    assert parsed == datetime(2025, 4, 1, tzinfo=timezone.utc)


def test_parse_reporting_month_missing_label_returns_none():
    assert parse_reporting_month_from_text("01.07.2026 print date only") is None
