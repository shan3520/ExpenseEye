"""
Amount-pattern detection robustness (remediation brief P1-8, P1-9).
"""
import pytest


def test_type_column_purchase_refund_loads(load_csv):
    """A 'Type' column of Purchase/Refund is a valid DrCr indicator: Purchase
    is a debit (negative), Refund a credit (positive). (P1-8)"""
    n, info, rows = load_csv(
        "Date,Description,Type,Amount\n"
        "2024-01-01,SHOP,Purchase,500\n"
        "2024-01-02,STORE,Refund,200\n"
    )
    assert n == 2
    assert info["amount_pattern"].startswith("DrCr")
    signs = {desc: amt for _, desc, amt in rows}
    assert signs["SHOP"] == -500.0
    assert signs["STORE"] == 200.0


def test_type_column_non_indicator_does_not_hijack(load_csv):
    """A 'Type' column whose values are NOT debit/credit indicators must not
    hijack the DrCr pattern; it falls through to the signed Amount. (P1-8)"""
    n, info, rows = load_csv(
        "Date,Description,Type,Amount\n"
        "2024-01-01,A,Online,-500\n"
        "2024-01-02,B,Online,-200\n"
    )
    assert n == 2
    assert info["amount_pattern"].startswith("Signed Amount")
    assert {amt for _, _, amt in rows} == {-500.0, -200.0}


def test_balance_only_statement_errors_clearly(load_csv):
    """A balance-only statement must not be loaded as if the running balance
    were the transaction amount; it raises an explanatory error. (P1-9)"""
    with pytest.raises(ValueError, match="[Bb]alance"):
        load_csv(
            "Date,Description,Balance\n"
            "2024-01-01,A,125000.00\n"
            "2024-01-02,B,103000.00\n"
        )


def test_ragged_row_skipped_not_aborted(load_csv):
    """One ragged (extra-field) row must not abort the whole file; valid rows
    load and the bad row is reported in the exception list (P1-7 / P2-13)."""
    n, info, rows = load_csv(
        "Date,Description,Amount\n"
        "2024-01-01,COFFEE,-100\n"
        "2024-01-02,X,Y,-50\n"      # 4 fields where 3 expected
        "2024-01-03,TEA,-30\n"
    )
    assert n == 2
    assert info["rows_skipped"] == 1
    assert len(info["skipped_rows"]) == 1
    assert "Malformed" in info["skipped_rows"][0]["reason"]


def test_bad_amount_row_reported_with_reason(load_csv):
    """A row with an unparseable amount is skipped WITH a reason and its raw
    values, not silently (P2-13)."""
    n, info, rows = load_csv(
        "Date,Description,Amount\n"
        "2024-01-01,GOOD,-100\n"
        "2024-01-02,BADAMT,notanumber\n"
    )
    assert n == 1
    assert info["rows_skipped"] == 1
    detail = info["skipped_rows"][0]
    assert detail["row"] == 1
    assert "amount" in detail["reason"].lower()
