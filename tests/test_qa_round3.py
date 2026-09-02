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


# ----- calendar drift in the reconciliation schedule ----------------------- #

def test_monthly_schedule_does_not_drift_off_calendar(tmp_path):
    """A monthly bill lands on the same DAY OF MONTH, not every N days.
    Projecting expected dates with a fixed day count accumulated ~half a day of
    error per cycle, so on a long statement the projection drifted outside the
    tolerance and every later charge was reported BOTH as missing AND as
    unscheduled -- a fake match rate with a doubly wrong exception list."""
    import datetime as dt
    from core.loader import load_csv_to_db
    from core.reconcile import reconcile_recurring

    lines = ["Date,Description,Amount"]
    d = dt.date(2022, 1, 3)
    for _ in range(60):                       # five years, always the 3rd
        lines.append(f"{d},UPI-NETFLIX INDIA,-649")
        d = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 3)

    csv_path = os.path.join(tmp_path, "r.csv")
    with open(csv_path, "w", newline="") as f:
        f.write("\n".join(lines) + "\n")
    db = os.path.join(tmp_path, "r.db")
    load_csv_to_db(csv_path, db)

    summary = reconcile_recurring(db)["summary"]
    assert summary["match_rate"] == 100.0, summary
    assert summary["missing"] == 0
    assert summary["unscheduled"] == 0


def test_genuinely_missing_charges_are_still_reported(tmp_path):
    """The drift fix must remove only PHANTOM exceptions: a real gap in the
    billing must still be reported."""
    import datetime as dt
    from core.loader import load_csv_to_db
    from core.reconcile import reconcile_recurring

    lines = ["Date,Description,Amount"]
    d = dt.date(2022, 1, 3)
    for i in range(24):
        if i not in (10, 11):                 # two months genuinely skipped
            lines.append(f"{d},UPI-NETFLIX INDIA,-649")
        d = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 3)

    csv_path = os.path.join(tmp_path, "g.csv")
    with open(csv_path, "w", newline="") as f:
        f.write("\n".join(lines) + "\n")
    db = os.path.join(tmp_path, "g.db")
    load_csv_to_db(csv_path, db)

    summary = reconcile_recurring(db)["summary"]
    assert summary["missing"] == 2, summary
    assert summary["match_rate"] < 100.0


def test_month_end_billing_clamps_to_short_months(tmp_path):
    """A bill on the 31st must project onto the 28th/29th of February rather
    than overflowing into March."""
    from core.reconcile import _add_months
    import pandas as pd
    assert _add_months(pd.Timestamp("2022-01-31"), 1) == pd.Timestamp("2022-02-28")
    assert _add_months(pd.Timestamp("2024-01-31"), 1) == pd.Timestamp("2024-02-29")
    assert _add_months(pd.Timestamp("2022-12-15"), 1) == pd.Timestamp("2023-01-15")
    assert _add_months(pd.Timestamp("2022-01-03"), 3) == pd.Timestamp("2022-04-03")


# ----- forecast: one-off damping, chosen by back-test ---------------------- #

def _statement(months, per_month, extra=None):
    """A simple multi-month statement; `extra` adds (date, desc, amount) rows."""
    lines = ["Date,Description,Amount"]
    for m in months:
        for d, (desc, amt) in enumerate(per_month, start=1):
            lines.append(f"2025-{m:02d}-{d:02d},{desc},-{amt}")
    for row in (extra or []):
        lines.append(",".join(str(x) for x in row))
    return "\n".join(lines) + "\n"


def _forecast_for(tmp_path, text, name="f"):
    from core.loader import load_csv_to_db
    from core.forecast import forecast_cashflow
    csv_path = os.path.join(tmp_path, f"{name}.csv")
    with open(csv_path, "w", newline="") as fh:
        fh.write(text)
    db = os.path.join(tmp_path, f"{name}.db")
    load_csv_to_db(csv_path, db)
    return forecast_cashflow(db)


def test_headline_totals_come_from_one_model(tmp_path):
    """"Next 30 days" summed an independent DAILY model while "next month" came
    from a MONTHLY one, so the two headline figures were different forecasts and
    contradicted each other on screen by 47%."""
    per_month = [(f"MERCHANT {i}", 500 + i * 37) for i in range(1, 26)]
    fc = _forecast_for(tmp_path, _statement(range(1, 9), per_month))
    assert fc["success"], fc
    ratio = fc["next_30_day_total"] / fc["next_month_total"]
    # Pure arithmetic now: the month forecast scaled by 30 / days-in-month.
    assert 30 / 31 - 0.001 <= ratio <= 1.0 + 0.001, (ratio, fc["totals_basis"])


def test_recurring_charges_are_never_damped(tmp_path):
    """A size-only outlier test flags RENT every month -- the single most
    recurring charge there is, and the exact rhythm the forecast projects."""
    from core.forecast import _one_off_mask, _load_expenses
    from core.loader import load_csv_to_db

    per_month = [("UPI-RENT LANDLORD", 18500)] + [
        (f"MERCHANT {i}", 400 + i * 23) for i in range(1, 25)
    ]
    csv_path = os.path.join(tmp_path, "r.csv")
    with open(csv_path, "w", newline="") as fh:
        fh.write(_statement(range(1, 9), per_month))
    db = os.path.join(tmp_path, "r.db")
    load_csv_to_db(csv_path, db)

    df = _load_expenses(db)
    mask = _one_off_mask(df, db)
    flagged = df[mask]["description"].tolist()
    assert not any("RENT" in d for d in flagged), flagged


def test_one_off_damping_must_win_the_backtest(tmp_path):
    """Damping is a hypothesis, not an article of faith. On a statement with no
    distorting one-off it must not be applied at all."""
    per_month = [(f"MERCHANT {i}", 500 + i * 31) for i in range(1, 26)]
    fc = _forecast_for(tmp_path, _statement(range(1, 9), per_month))
    assert fc["one_offs_excluded_from_training"] is False
    assert fc["one_offs"]["count"] == 0


def test_single_huge_charge_is_excluded_and_improves_accuracy(tmp_path):
    """The case this exists for: one large one-off drags the trend up and the
    model then predicts another one."""
    per_month = [(f"MERCHANT {i}", 500 + i * 31) for i in range(1, 26)]
    text = _statement(range(1, 9), per_month, extra=[("2025-05-14", "ONE OFF LAPTOP", -85000)])
    fc = _forecast_for(tmp_path, text)
    assert fc["one_offs_excluded_from_training"] is True, fc["one_offs"]
    assert fc["one_offs"]["count"] == 1
    assert "LAPTOP" in fc["one_offs"]["charges"][0]["description"]
    # The rejected candidate is published beside the chosen one, and is worse.
    assert fc["accuracy"]["mae"] < fc["accuracy_alternative"]["mae"]


def test_charted_history_still_shows_the_one_off(tmp_path):
    """Excluded from what the model LEARNS, never removed from what is shown."""
    per_month = [(f"MERCHANT {i}", 500 + i * 31) for i in range(1, 26)]
    text = _statement(range(1, 9), per_month, extra=[("2025-05-14", "ONE OFF LAPTOP", -85000)])
    fc = _forecast_for(tmp_path, text)
    may = next(m for m in fc["monthly"]["history"] if m["month"] == "2025-05")
    other = next(m for m in fc["monthly"]["history"] if m["month"] == "2025-04")
    assert may["spend"] > other["spend"] + 80000, "the spike was scrubbed from the chart"


# ----- anomaly precision: a pattern is not an anomaly ---------------------- #

def _anomalies_for(tmp_path, lines, name="an"):
    from core.loader import load_csv_to_db
    from core.anomaly import detect_anomalies
    csv_path = os.path.join(tmp_path, f"{name}.csv")
    with open(csv_path, "w", newline="") as fh:
        fh.write("\n".join(["Date,Description,Amount"] + lines) + "\n")
    db = os.path.join(tmp_path, f"{name}.db")
    load_csv_to_db(csv_path, db)
    return detect_anomalies(db)


def _cheap_transport(n=40):
    """Bike taxis: small, frequent, and the reason petrol looks huge."""
    return [
        f"2025-{(i % 8) + 1:02d}-{(i % 27) + 1:02d},UPI-RAPIDO BIKE TAXI,-{60 + (i * 7) % 120}"
        for i in range(n)
    ]


def test_repeat_high_charges_are_not_anomalies(tmp_path):
    """Petrol shares "transport" with bike taxis, so every fill scores a huge
    CATEGORY z-score. 27 of them is a pattern, not 27 anomalies."""
    petrol = [
        f"2025-{(i % 8) + 1:02d}-{(i % 25) + 2:02d},POS INDIAN OIL PETROL,-{1400 + (i * 53) % 900}"
        for i in range(20)
    ]
    res = _anomalies_for(tmp_path, _cheap_transport() + petrol)
    flagged = [a["description"] for a in res["anomalies"]]
    assert not any("PETROL" in d for d in flagged), flagged
    assert res["routine_for_merchant_suppressed"] >= 1


def test_suppression_is_reported_not_silent(tmp_path):
    """The difference between "found nothing" and "ruled these out" must stay
    visible in the response."""
    petrol = [
        f"2025-{(i % 8) + 1:02d}-{(i % 25) + 2:02d},POS INDIAN OIL PETROL,-{1400 + (i * 53) % 900}"
        for i in range(20)
    ]
    res = _anomalies_for(tmp_path, _cheap_transport() + petrol)
    assert "routine_for_merchant_suppressed" in res
    assert res["routine_for_merchant_suppressed"] > 0


def test_genuine_outlier_at_a_familiar_merchant_still_flagged(tmp_path):
    """The suppression must not become a blanket amnesty: a merchant you use
    constantly can still make one charge that does not belong."""
    amazon = [
        f"2025-{(i % 8) + 1:02d}-{(i % 25) + 2:02d},UPI-AMAZON SELLER SVCS,-{300 + (i * 91) % 2600}"
        for i in range(30)
    ]
    res = _anomalies_for(tmp_path, amazon + ["2025-06-18,UPI-AMAZON SELLER SVCS,-84999"])
    flagged = [a for a in res["anomalies"] if abs(a["spend"] - 84999) < 1]
    assert flagged, [a["description"] for a in res["anomalies"]]
    assert "merchant's usual" in flagged[0]["explanation"]


def test_first_time_merchant_cannot_excuse_itself(tmp_path):
    """A merchant with no track record here has no "usual" to hide behind."""
    res = _anomalies_for(
        tmp_path,
        _cheap_transport() + ["2025-05-14,UPI-CROMA ELECTRONICS,-78999"],
    )
    assert any(abs(a["spend"] - 78999) < 1 for a in res["anomalies"]), \
        [a["description"] for a in res["anomalies"]]


# ----- split narration across two columns ---------------------------------- #
# Shape taken from a real export (synthetic contents): the narration lives in a
# RAIL column that is always present and a COUNTERPARTY column that is blank for
# ATM withdrawals, interest and cheques.

SPLIT = (
    "date,DrCr,amount,balance,mode,name\n"
    "2025-01-02,Db,930.0,462362.87,UPI,MERCHANTONE\n"
    "2025-01-03,Db,10000.0,452362.87,ATM,\n"
    "2025-01-05,Cr,52521.0,504883.87,NEFT,\n"
    "2025-01-07,Db,275.0,504608.87,UPI,MERCHANTTWO\n"
    "2025-01-09,Db,18.0,504590.87,SMS CHARGES,\n"
    "2025-01-11,Db,200000.0,304590.87,CHEQUE,\n"
    "2025-01-13,Db,563.0,304027.87,UPI,FLIPKART\n"
    "2025-01-15,Cr,7.09,304034.96,ECS,\n"
)


def test_split_narration_is_recombined(load_csv):
    """Taking only the counterparty column stored every ATM, NEFT, cheque and
    charge row as "UNKNOWN" -- 27% of a real statement -- and threw away the
    rail, which is the most categorizable field in the file."""
    n, info, rows = load_csv(SPLIT)
    assert info["description_column"] == "mode + name"
    descriptions = [r[1] for r in rows]
    assert "UNKNOWN" not in descriptions, descriptions
    assert "UPI MERCHANTONE" in descriptions
    assert "ATM" in descriptions
    assert "CHEQUE" in descriptions


def test_complete_description_column_is_left_alone(load_csv):
    """The recombination is gated on GAPS. A well-formed export must be
    untouched, or every description would grow noise columns."""
    text = (
        "Date,Description,Amount\n"
        "2025-01-02,NETFLIX STREAMING,-649\n"
        "2025-01-03,SWIGGY ORDER,-320\n"
        "2025-01-04,BIGBASKET DAILY,-1450\n"
    )
    n, info, rows = load_csv(text)
    assert info["description_column"] == "Description"
    assert [r[1] for r in rows] == ["NETFLIX STREAMING", "SWIGGY ORDER", "BIGBASKET DAILY"]


def test_a_category_column_is_never_folded_into_the_description(load_csv):
    """Appending a label column would hand the classifier the answer and make
    its reported accuracy meaningless."""
    text = (
        "Date,Description,Amount,Category\n"
        "2025-01-02,NETFLIX STREAMING,-649,Entertainment\n"
        "2025-01-03,,-320,Dining\n"          # a gap, so the rule is live
        "2025-01-04,BIGBASKET DAILY,-1450,Groceries\n"
    )
    n, info, rows = load_csv(text)
    assert "Category" not in info["description_column"]
    assert not any("Entertainment" in r[1] for r in rows), [r[1] for r in rows]


# ----- rule matching is prefix-anchored ------------------------------------ #

def test_rules_match_truncated_merchant_names():
    """Banks truncate: DOMINOSP, AMAZONPA. A trailing word boundary would
    refuse all of them."""
    from core.categorizer import _rule_category
    assert _rule_category("UPI DOMINOSP") == "dining"
    assert _rule_category("UPI AMAZONPA") == "shopping"
    assert _rule_category("UPI FLIPKART") == "shopping"


def test_rules_do_not_match_mid_word():
    """Bare substring matching let "atm" fire inside "BATMAN" and "TREATMENT"."""
    from core.categorizer import _rule_category
    assert _rule_category("BATMAN COLLECTIBLES") != "cash"
    assert _rule_category("TREATMENT CENTRE") != "cash"
    assert _rule_category("ATM WDL") == "cash"


def test_merchant_categories_beat_the_transfer_rail():
    """Every UPI row contains "upi"; the merchant must still win, or 73% of an
    Indian statement collapses into "transfers"."""
    from core.categorizer import _rule_category
    assert _rule_category("UPI SWIGGY ORDER") == "dining"
    assert _rule_category("UPI-NETFLIX-NETFLIX@YBL") == "subscriptions"
    assert _rule_category("UPI SOMEPERSONNAME") == "transfers"


def test_banking_rails_have_honest_categories():
    """Cash leaving the account, and bank charges, are knowable -- filing them
    under "uncategorized" reads as a failure to classify rather than a limit of
    the data."""
    from core.categorizer import _rule_category
    assert _rule_category("ATM") == "cash"
    assert _rule_category("CHEQUE") == "transfers"
    assert _rule_category("SMS CHARGES") == "fees"
    assert _rule_category("DEBIT CARD ANNUAL") == "fees"
