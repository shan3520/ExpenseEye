"""
ExpenseEye reconciliation — closing one finance-ops loop.

Answers the question a finance controller actually asks of a statement:
"every charge we EXPECTED to recur — did it actually land, on time, at the
right amount, and what could we not account for?"

Expected ledger : the recurring series detected by core.subscriptions
                  (merchant + cadence + amount band).
Actual ledger   : the transactions in the session database.

The loop reports a match rate over the whole expected batch plus a two-sided
exception list — expected-but-missing (a skipped or failed charge) and
actual-but-unscheduled (a duplicate or off-cycle charge). Nothing is
cherry-picked: every expected occurrence is accounted for as matched,
matched-with-variance, or missing.
"""
import sqlite3
from datetime import timedelta

import pandas as pd

from core.subscriptions import detect_subscriptions, normalize_description

# A charge may land this fraction of its cadence early/late and still count as
# the scheduled occurrence (clamped to a sane number of days).
_DATE_TOL_FRAC = 0.35
_DATE_TOL_MIN_DAYS = 3
_DATE_TOL_MAX_DAYS = 10
# Amount band around the series median before a match is flagged as variance.
_AMOUNT_TOL_FRAC = 0.15
_AMOUNT_TOL_ABS = 50.0
# A series whose last charge predates the statement end by more than this many
# cadences is reported as lapsed rather than generating phantom "missing" rows.
_LAPSE_CADENCES = 1.5


def _load_expenses(db_path):
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(
            "SELECT txn_date, description, amount FROM transactions "
            "WHERE amount < 0 ORDER BY txn_date",
            conn,
        )
    finally:
        conn.close()
    if df.empty:
        return df
    df["txn_date"] = pd.to_datetime(df["txn_date"])
    df["norm"] = df["description"].map(normalize_description)
    df["mag"] = df["amount"].abs()
    return df


def reconcile_recurring(db_path):
    """
    Reconcile expected recurring charges against what the statement actually
    contains. Returns a JSON-serializable dict.
    """
    df = _load_expenses(db_path)
    if df.empty:
        return {"success": False, "error": "No expense transactions to reconcile."}

    subs = detect_subscriptions(db_path)
    if not subs:
        return {
            "success": False,
            "error": "No recurring series detected, so there is nothing to reconcile.",
        }

    statement_end = df["txn_date"].max()
    matched, missing, unscheduled, series_report = [], [], [], []
    total_expected = 0

    for sub in subs:
        key = normalize_description(sub["description"])
        median_mag = abs(sub["amount"])
        amt_tol = max(_AMOUNT_TOL_FRAC * median_mag, _AMOUNT_TOL_ABS)
        cadence = float(sub["avg_gap"])
        if cadence <= 0:
            continue
        date_tol = min(max(_DATE_TOL_FRAC * cadence, _DATE_TOL_MIN_DAYS), _DATE_TOL_MAX_DAYS)

        actuals = df[df["norm"] == key].sort_values("txn_date").copy()
        if actuals.empty:
            continue
        actuals["used"] = False

        first = actuals["txn_date"].iloc[0]
        last = actuals["txn_date"].iloc[-1]

        # Project the expected schedule across the OBSERVED life of the series.
        # Projecting past the last charge would invent missing rows for a
        # subscription that was simply cancelled, so a lapse is reported
        # separately instead of being counted as a failure.
        expected_dates, i = [], 0
        while True:
            d = first + timedelta(days=cadence * i)
            if d > last + timedelta(days=date_tol):
                break
            expected_dates.append(d)
            i += 1
            if i > 500:  # defensive bound
                break

        series_matched = series_missing = series_variance = 0

        for exp_date in expected_dates:
            total_expected += 1
            window = actuals[
                (~actuals["used"])
                & ((actuals["txn_date"] - exp_date).abs() <= timedelta(days=date_tol))
            ]
            if window.empty:
                missing.append({
                    "merchant": sub["description"],
                    "expected_date": exp_date.strftime("%Y-%m-%d"),
                    "expected_amount": -round(median_mag, 2),
                    "frequency": sub["frequency"],
                    "reason": "No charge found within "
                              f"{date_tol:.0f} days of the expected date",
                })
                series_missing += 1
                continue

            # Nearest candidate in the window wins.
            idx = (window["txn_date"] - exp_date).abs().idxmin()
            actuals.loc[idx, "used"] = True
            row = actuals.loc[idx]
            delta = abs(float(row["mag"]) - median_mag)
            variance = delta > amt_tol
            if variance:
                series_variance += 1
            series_matched += 1
            matched.append({
                "merchant": sub["description"],
                "expected_date": exp_date.strftime("%Y-%m-%d"),
                "actual_date": row["txn_date"].strftime("%Y-%m-%d"),
                "day_drift": int((row["txn_date"] - exp_date).days),
                "expected_amount": -round(median_mag, 2),
                "actual_amount": round(float(row["amount"]), 2),
                "amount_variance": round(delta, 2),
                "status": "matched_with_variance" if variance else "matched",
            })

        # Charges from this merchant that no scheduled slot claimed.
        for _, row in actuals[~actuals["used"]].iterrows():
            unscheduled.append({
                "merchant": sub["description"],
                "txn_date": row["txn_date"].strftime("%Y-%m-%d"),
                "amount": round(float(row["amount"]), 2),
                "reason": "Charge from a recurring merchant that no expected "
                          "occurrence accounts for (possible duplicate or off-cycle bill)",
            })

        lapsed = (statement_end - last).days > _LAPSE_CADENCES * cadence
        series_report.append({
            "merchant": sub["description"],
            "frequency": sub["frequency"],
            "cadence_days": round(cadence, 1),
            "expected": len(expected_dates),
            "matched": series_matched,
            "missing": series_missing,
            "with_variance": series_variance,
            "lapsed": bool(lapsed),
            "last_seen": last.strftime("%Y-%m-%d"),
        })

    match_rate = (len(matched) / total_expected) if total_expected else 0.0
    clean = len(matched) - sum(1 for m in matched if m["status"] == "matched_with_variance")

    return {
        "success": True,
        "method": "Expected recurring ledger vs actual statement charges "
                  "(cadence + amount-band matching)",
        "tolerances": {
            "date_days": "35% of cadence, clamped to 3-10 days",
            "amount": f"max({int(_AMOUNT_TOL_FRAC * 100)}% of median, Rs {int(_AMOUNT_TOL_ABS)})",
        },
        "summary": {
            "series_reconciled": len(series_report),
            "expected_occurrences": total_expected,
            "matched": len(matched),
            "matched_clean": clean,
            "matched_with_variance": len(matched) - clean,
            "missing": len(missing),
            "unscheduled": len(unscheduled),
            "match_rate": round(match_rate * 100, 1),
        },
        "series": series_report,
        "matched": matched,
        "exceptions": {
            "missing": missing,
            "unscheduled": unscheduled,
        },
    }
