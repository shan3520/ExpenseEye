"""
coerce_amount format coverage (remediation brief P2-14).

Against the audited HEAD, the European decimal-comma, space-thousands,
leading-currency-code, trailing-minus and malformed-separator cases fail.
"""
import pytest

from core.loader import coerce_amount


@pytest.mark.parametrize("raw, expected", [
    # Previously-correct cases must stay correct (no regression).
    ("1,250.50", 1250.5),
    ("(22,000.00)", -22000.0),
    ("85,000.00 CR", 85000.0),
    ("₹2,300", 2300.0),      # ₹2,300
    ("$1,200", 1200.0),
    ("49,429.72 CR", 49429.72),
    ("1,234,567", 1234567.0),
    ("119.00", 119.0),
    ("-1500.00", -1500.0),
    ("0", 0.0),
    # Newly-fixed cases (P2-14).
    ("1.234,56", 1234.56),        # European decimal comma
    ("1 234,56", 1234.56),        # space thousands + decimal comma
    ("INR 500", 500.0),           # leading currency code
    ("500-", -500.0),             # trailing minus
])
def test_coerce_amount_values(raw, expected):
    got = coerce_amount(raw)
    assert got == pytest.approx(expected)


@pytest.mark.parametrize("raw", ["1,2,3", "", "abc", "nan", None, "-", "."])
def test_coerce_amount_rejects_garbage(raw):
    assert coerce_amount(raw) is None
