"""
Regression tests for the third QA round.

Every case here comes from driving the app with bank-statement shapes it had
not been tested against before, rather than from re-reading the code: a real
HDFC-style export with a banner preamble, and a European semicolon export.
"""
import os
import sqlite3

import pytest

HDFC = """Statement of Account
Account No: XXXXXXXX4471   Branch: KORAMANGALA
Period: 01/03/2025 to 31/08/2025

Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance
01/03/25,NEFT-DR-HOUSING RENT,960132164,01/03/25,18500.00,,126800.00
15/03/25,UPI-NETFLIX-NETFLIX@YBL,580849256,15/03/25,649.00,,126151.00
28/03/25,SALARY CREDIT-ACME LTD,643377739,28/03/25,,92000.00,218151.00

*** End of Statement ***
"""


# ----- header row detection ------------------------------------------------ #

def test_banner_preamble_shorter_than_header_is_skipped(load_csv):
    """A preamble line with fewer fields than the header used to make the
    pandas preview raise, and the bare fallback then chose row 0 -- the banner
    line -- so the upload was rejected with "Your CSV has: [Statement of
    Account]". csv.reader has no field-count constraint."""
    n, info, rows = load_csv(HDFC)
    assert n == 3
    assert info["date_column"] == "Date"
    assert info["description_column"] == "Narration"


def test_trailing_junk_line_is_reported_not_fatal(load_csv):
    """The '*** End of Statement ***' footer must be skipped WITH a reason,
    not silently dropped and not fatal to the other rows."""
    n, info, rows = load_csv(HDFC)
    assert n == 3
    assert info["rows_skipped"] == 1
    assert any("End of Statement" in s["reason"] for s in info["skipped_rows"])


# ----- column name normalization ------------------------------------------- #

def test_abbreviated_column_names_with_periods_match(load_csv):
    """"Withdrawal Amt." normalized to "withdrawalamt." and so never matched
    the "withdrawalamt" alias written for that very column."""
    n, info, rows = load_csv(HDFC)
    assert info["amount_pattern"].startswith("Debit/Credit")
    amounts = [r[2] for r in rows]
    assert -18500.0 in amounts          # withdrawal -> negative
    assert 92000.0 in amounts           # deposit    -> positive


def test_normalizer_drops_all_punctuation():
    from core.loader import normalize_column_name as n
    assert n("Withdrawal Amt.") == "withdrawalamt"
    assert n("Chq./Ref.No.") == "chqrefno"
    assert n("Dr/Cr") == "drcr"


# ----- currency-qualified amount headers ----------------------------------- #

EURO = (
    "Txn Date;Particulars;Dr/Cr;Amount (INR);Balance\n"
    "05-01-2025;EDEKA MARKT;DR;1.234,56;10.000,00\n"
    "12-01-2025;GEHALT;CR;2.500,00;12.500,00\n"
    "19-01-2025;EDEKA MARKT;DR;987,10;11.512,90\n"
)


def test_currency_qualified_amount_column(load_csv):
    """"Amount (INR)" is the same column as "Amount"; it used to fall through
    to the "that is a running balance" error instead."""
    n, info, rows = load_csv(EURO)
    assert n == 3
    assert [r[2] for r in rows] == [-1234.56, 2500.0, -987.10]


@pytest.mark.parametrize("cols", [
    ["Date", "Desc", "Amount Outstanding", "Balance"],
    ["Date", "Desc", "Amount Due"],
])
def test_currency_suffix_match_is_not_a_loose_prefix(cols):
    """The qualifier allow-list must not turn into a prefix match: an
    "Amount Outstanding" column is not a transaction amount."""
    from core.loader import detect_amount_pattern
    with pytest.raises(ValueError):
        detect_amount_pattern(cols)


# ----- subscription precision ---------------------------------------------- #

def _variable_merchant_csv():
    """36 food deliveries at random-ish amounts, 5 days apart, plus a real
    fixed-price subscription at the same cadence class."""
    lines = ["Date,Description,Amount"]
    import datetime as dt
    d = dt.date(2025, 1, 1)
    amounts = [188, 241, 326, 623, 258, 410, 417, 402, 430, 380,
               512, 199, 604, 355, 470, 288, 333, 561]
    for i, a in enumerate(amounts):
        lines.append(f"{d + dt.timedelta(days=i * 5)},UPI-ZOMATO ONLINE,-{a}")
    for m in range(1, 7):
        lines.append(f"2025-{m:02d}-03,UPI-NETFLIX INDIA,-649")
    return "\n".join(lines) + "\n"


def test_variable_spend_merchant_is_not_a_subscription(tmp_path):
    """A lucky slice of a variable-amount merchant used to pass as a
    FORTNIGHTLY subscription, which then flooded reconciliation with bogus
    "unscheduled" exceptions and inflated the match rate."""
    from core.loader import load_csv_to_db
    from core.subscriptions import detect_subscriptions

    csv_path = os.path.join(tmp_path, "v.csv")
    with open(csv_path, "w", newline="") as f:
        f.write(_variable_merchant_csv())
    db = os.path.join(tmp_path, "v.db")
    load_csv_to_db(csv_path, db)

    subs = detect_subscriptions(db)
    names = " ".join(s["description"] for s in subs).upper()
    assert "ZOMATO" not in names, "variable food spend admitted as a subscription"
    assert "NETFLIX" in names, "real fixed-price subscription was lost"


def test_fixed_price_series_survives_low_coverage(tmp_path):
    """The coverage bar alone would reject a real subscription buried in
    one-off spend at the same merchant, so identical amounts must still pass."""
    from core.loader import load_csv_to_db
    from core.subscriptions import detect_subscriptions

    lines = ["Date,Description,Amount"]
    for m in range(1, 7):                       # the subscription
        lines.append(f"2025-{m:02d}-08,UPI-AMAZON PRIME,-1499")
    for i, a in enumerate([230, 4100, 780, 15600, 320, 2450,   # the shopping
                           990, 6700, 145, 3300, 880, 5200]):
        lines.append(f"2025-{(i % 6) + 1:02d}-{(i % 20) + 1:02d},UPI-AMAZON PRIME,-{a}")

    csv_path = os.path.join(tmp_path, "a.csv")
    with open(csv_path, "w", newline="") as f:
        f.write("\n".join(lines) + "\n")
    db = os.path.join(tmp_path, "a.db")
    load_csv_to_db(csv_path, db)

    subs = detect_subscriptions(db)
    assert any(abs(s["amount"] + 1499) < 1 for s in subs), \
        "fixed-price subscription rejected purely for low merchant coverage"


# ----- one categorization path --------------------------------------------- #

def test_anomaly_and_categorizer_agree(tmp_path):
    """Anomaly detection called model.predict() raw while the categorizer
    applied a confidence threshold and a rule fallback, so the same charge was
    labelled differently in two cards -- and the z-score was measured against
    the wrong category's baseline."""
    from core.loader import load_csv_to_db
    from core.anomaly import detect_anomalies
    from core.categorizer import categorize_transactions

    lines = ["Date,Description,Amount"]
    for i in range(12):
        lines.append(f"2025-0{(i % 6) + 1}-1{i % 9},UPI-AMAZON SELLER SVCS,-{900 + i * 40}")
    lines.append("2025-06-18,UPI-AMAZON SELLER SVCS,-84999")

    csv_path = os.path.join(tmp_path, "c.csv")
    with open(csv_path, "w", newline="") as f:
        f.write("\n".join(lines) + "\n")
    db = os.path.join(tmp_path, "c.db")
    load_csv_to_db(csv_path, db)

    anomalies = detect_anomalies(db)["anomalies"]
    assert anomalies, "the 84,999 outlier should be flagged"
    flagged = anomalies[0]

    cats = categorize_transactions(db)["transactions"]
    same = [t for t in cats if abs(t["amount"] - flagged["amount"]) < 0.01]
    assert same and same[0]["category"] == flagged["category"], (
        f"anomaly says {flagged['category']!r}, categorizer says "
        f"{same[0]['category']!r} for the same transaction"
    )
