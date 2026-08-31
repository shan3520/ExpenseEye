"""
Date-format detection regression tests (remediation brief P0-2).

Against the audited HEAD, `test_iso_dates_not_transposed` fails: ISO-8601 dates
were parsed day-first and silently transposed (2024-03-01 stored as 2024-01-03).
"""
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def test_iso_dates_not_transposed(load_csv):
    # 2024-03-01 must store as 1 March, not 3 January (the P0-2 corruption).
    _, info, rows = load_csv(
        "Date,Description,Amount\n2024-03-01,COFFEE,-100\n2024-05-11,BILL,-300\n"
    )
    assert info["date_format"].startswith("YYYY-MM-DD")
    assert rows[0][0] == "2024-03-01"
    assert rows[1][0] == "2024-05-11"


def test_dayfirst_ddmm_still_parses(load_csv):
    _, info, rows = load_csv(
        "Date,Description,Amount\n13/03/2024,A,-100\n05/03/2024,B,-50\n"
    )
    assert info["date_format"] == "DD/MM/YYYY"
    assert rows[0][0] == "2024-03-13"


def test_monthfirst_mmdd_still_parses(load_csv):
    _, info, rows = load_csv(
        "Date,Description,Amount\n03/13/2024,A,-100\n03/05/2024,B,-50\n"
    )
    assert info["date_format"] == "MM/DD/YYYY"
    assert rows[0][0] == "2024-03-13"


def test_iso_fixture_loads_clean(load_csv):
    """C5 baseline: the synthetic ISO fixture loads every row with 0 skipped,
    DrCr detected, and the blank-header narration resolved by the content
    heuristic; signs are applied correctly."""
    path = os.path.join(DATA_DIR, "sample_statement_iso.csv")
    n, info, rows = load_csv(path, is_path=True)
    assert n == 73
    assert info["rows_skipped"] == 0
    assert info["amount_pattern"].startswith("DrCr")
    assert info["date_format"].startswith("YYYY-MM-DD")
    signs = {desc: amt for _, desc, amt in rows}
    assert signs["RENT PAYMENT LANDLORD"] < 0      # debit
    assert signs["SALARY CREDIT ACME CORP"] > 0    # credit
