"""
ExpenseEye subscription detection.

Groups recurring charges by a NORMALIZED merchant description and an amount
BUCKET (not exact float equality), so real subscriptions whose price drifts
with GST revisions, plan changes or FX are still detected (P0-3). Cadence is
judged from the MEDIAN gap with a tolerance band, so a single skipped or
early-billed month no longer disqualifies the series.

Detection is a pure read: it never writes to the database (P2-16).
"""
import re
import sqlite3

import numpy as np
import pandas as pd

# A charge belongs to a subscription series if its magnitude is within this
# fraction (or absolute floor) of the series median — tolerates price drift.
_AMOUNT_TOL_FRAC = 0.15
_AMOUNT_TOL_ABS = 50.0
# Recognized cadences: (label, low_days, high_days).
_CADENCES = [
    ("WEEKLY", 6, 8),
    ("FORTNIGHTLY", 12, 16),
    ("MONTHLY", 25, 35),
    ("QUARTERLY", 84, 100),
]
# Reject a series whose gaps are more irregular than this (MAD / median gap).
_MAX_GAP_DISPERSION = 0.4


def normalize_description(description):
    """
    Normalize a merchant description for grouping: lowercase, drop long digit
    runs (card / reference / transaction numbers), keep letters, collapse
    whitespace. "NETFLIX *REF12345" and "Netflix" both become "netflix".
    """
    d = str(description).lower()
    d = re.sub(r"\d{3,}", " ", d)          # ref / card / txn numbers
    d = re.sub(r"[^a-z& ]+", " ", d)       # keep letters and ampersand
    d = re.sub(r"\s+", " ", d).strip()
    return d


def _classify_cadence(median_gap):
    for label, lo, hi in _CADENCES:
        if lo <= median_gap <= hi:
            return label
    return None


def detect_subscriptions(db_path="smartspend.db"):
    """
    Detect recurring subscriptions in a session database.

    Returns a list of dicts, each with:
      - description : a representative raw description
      - amount      : median charge (negative, matching the stored sign)
      - amount_min / amount_max : observed range (negative) so a price change
                                  is visible
      - frequency   : WEEKLY | FORTNIGHTLY | MONTHLY | QUARTERLY
      - avg_gap     : median days between charges
      - occurrences : number of charges in the series
    """
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(
            "SELECT txn_date, description, amount FROM transactions "
            "WHERE description != 'UNKNOWN' AND amount < 0 "
            "ORDER BY txn_date",
            conn,
        )
    finally:
        conn.close()

    if df.empty:
        return []

    df["txn_date"] = pd.to_datetime(df["txn_date"])
    df["norm"] = df["description"].map(normalize_description)
    df["mag"] = df["amount"].abs()

    subscriptions = []

    for norm, group in df.groupby("norm"):
        if not norm or len(group) < 3:
            continue

        # Keep the dominant amount cluster (within tolerance of the median),
        # so an occasional off-price charge doesn't break the series but a
        # genuinely different amount isn't merged in.
        median_amt = float(group["mag"].median())
        tol = max(_AMOUNT_TOL_FRAC * median_amt, _AMOUNT_TOL_ABS)
        series = group[(group["mag"] - median_amt).abs() <= tol].sort_values("txn_date")
        if len(series) < 3:
            continue

        gaps = series["txn_date"].diff().dt.days.dropna().to_numpy()
        if len(gaps) == 0:
            continue
        median_gap = float(np.median(gaps))
        mad = float(np.median(np.abs(gaps - median_gap)))

        frequency = _classify_cadence(median_gap)
        if frequency is None:
            continue
        # Reject wildly irregular series (a one-off cluster of similar charges).
        if median_gap > 0 and mad > _MAX_GAP_DISPERSION * median_gap:
            continue

        rep = series["description"].mode()
        rep_desc = rep.iloc[0] if len(rep) else series["description"].iloc[0]
        mags = series["mag"]
        subscriptions.append({
            "description": rep_desc,
            "amount": -round(float(mags.median()), 2),
            "amount_min": -round(float(mags.max()), 2),
            "amount_max": -round(float(mags.min()), 2),
            "frequency": frequency,
            "avg_gap": round(median_gap, 1),
            "occurrences": int(len(series)),
        })

    subscriptions.sort(key=lambda s: s["occurrences"], reverse=True)
    return subscriptions
