from datetime import date
from decimal import Decimal

import pytest

from invoices.parsing import extract_text, find_issues, parse_invoice, to_date, to_decimal

from .pdfs import GOOD_INVOICE, MISMATCH_INVOICE, make_pdf


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,250.00", "1250.00"),
        ("1.250,00", "1250.00"),
        ("1 250,50", "1250.50"),
        ("980.5", "980.50"),
        ("12,345", "12345.00"),
    ],
)
def test_to_decimal_handles_both_separators(raw, expected):
    assert to_decimal(raw) == Decimal(expected)


def test_to_decimal_rejects_garbage():
    assert to_decimal("abc") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("2026-09-17", date(2026, 9, 17)), ("17.09.2026", date(2026, 9, 17)), ("17/09/2026", date(2026, 9, 17))],
)
def test_to_date_formats(raw, expected):
    assert to_date(raw) == expected


def test_to_date_invalid():
    assert to_date("31.02.2026") is None


def test_parse_text_from_a_real_pdf():
    parsed = parse_invoice(extract_text(make_pdf(GOOD_INVOICE)))
    assert parsed.vendor == "Lumora Studio"
    assert parsed.number == "INV-2026-0917"
    assert parsed.issue_date == date(2026, 9, 17)
    assert parsed.currency == "USD"
    assert parsed.total == Decimal("1250.00")
    assert [line.amount for line in parsed.lines] == [Decimal("300.00"), Decimal("950.00")]
    assert find_issues(parsed) == []


def test_currency_before_amount_and_total_mismatch():
    parsed = parse_invoice("\n".join(MISMATCH_INVOICE))
    assert parsed.currency == "EUR"
    assert find_issues(parsed) == ["total_mismatch:125.00!=165.00"]


def test_missing_fields_and_bad_line_math():
    parsed = parse_invoice("Widgets 3 x 10.00 = 31.00\nTotal: 31.00")
    issues = find_issues(parsed)
    assert "missing_number" in issues
    assert "missing_vendor" in issues
    assert "missing_currency" in issues
    assert "line_1_math" in issues
