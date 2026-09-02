"""
ExpenseEye Anomaly Detection.

Copyright (c) 2026 Shantanu (shan3520)
Original Repository: https://github.com/shan3520/expenseeye
License: MIT

Replaces the fixed overspending threshold with a statistical method: a robust
per-category z-score (using the median and the Median Absolute Deviation) over
individual expense transactions. Robust statistics are used so that a few
extreme outliers do not inflate the spread and mask other anomalies.

Each flagged transaction comes with a short human-readable explanation of why
it was unusual (how far above its category's typical amount it sits).
"""

import sqlite3

import numpy as np
import pandas as pd

from core.categorizer import predict_categories
from core.subscriptions import detect_subscriptions, normalize_description

# A transaction is flagged when its robust z-score exceeds this threshold.
_Z_THRESHOLD = 3.5
# Categories need at least this many transactions before we judge outliers.
_MIN_CATEGORY_COUNT = 5
# ...and a merchant needs at least this many charges before its OWN history can
# be used to excuse a charge. A category is a coarse bucket: petrol (900-2,600)
# shares "transport" with bike taxis (45-190), so every fill scores a huge
# category z-score. On the demo statement that flagged 28 charges of which 27
# were the same petrol station -- and something that happens 27 times is a
# pattern, not an anomaly. A charge must now be unusual for its category AND
# unusual for its own merchant, unless the merchant is too new to judge.
_MIN_MERCHANT_HISTORY = 4
# MAD -> std-dev consistency constant for normally distributed data.
_MAD_SCALE = 1.4826


def _category_for(descriptions):
    """Categorize descriptions exactly as the categorizer module does.

    Shares one implementation so the two never disagree about the same
    transaction, and so the per-category z-score baseline below is the same
    category the user is shown.
    """
    return [cat for cat, _conf, _src in predict_categories(list(descriptions))]


def detect_anomalies(db_path):
    """
    Flag unusual expense transactions using robust per-category z-scores.

    Returns a JSON-serializable dict with the flagged transactions (each with
    an explanation) and a per-category summary of the typical spend.
    """
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
        return {"success": False, "error": "No expense transactions to analyze."}

    # Known recurring subscriptions are excluded from anomaly CANDIDACY -- a
    # predictable monthly charge is a subscription, not an unexplained outlier,
    # and the two modules must not contradict each other (P2-15). They are kept
    # in the population, though, because dropping them would gut the statistics
    # on subscription-heavy statements and hide genuine one-off outliers.
    sub_keys = {normalize_description(s["description"]) for s in detect_subscriptions(db_path)}
    df["is_subscription"] = df["description"].fillna("").map(
        lambda d: normalize_description(d) in sub_keys
    )

    df["spend"] = df["amount"].abs()
    df["category"] = _category_for(df["description"].fillna("").astype(str))
    df["merchant"] = df["description"].fillna("").map(normalize_description)

    # Per-merchant robust baselines, for merchants seen often enough to have a
    # "usual" at all. Same statistics as the category baseline, one level down.
    merchant_stats = {}
    for _key, _grp in df.groupby("merchant"):
        _vals = _grp["spend"].to_numpy(dtype=float)
        if not _key or len(_vals) < _MIN_MERCHANT_HISTORY:
            continue
        _med = float(np.median(_vals))
        _mad = float(np.median(np.abs(_vals - _med)))
        _scale = _mad * _MAD_SCALE if _mad > 0 else float(_vals.std(ddof=0))
        merchant_stats[_key] = (_med, _scale)

    def _routine_for_merchant(key, spend):
        """Is this charge unremarkable for the merchant that made it?

        A merchant with no track record here cannot excuse anything, so a
        genuine one-off from a first-time merchant is still flagged.
        """
        stat = merchant_stats.get(key)
        if stat is None:
            return False
        med, scale = stat
        if scale <= 0:                      # every charge identical -> routine
            return abs(spend - med) < 1e-9
        return (spend - med) / scale < _Z_THRESHOLD

    anomalies = []
    category_stats = {}
    routine_suppressed = 0

    # Statement-wide robust baseline, used when a category is too thin to judge
    # on its own. Without it a lone large charge in a sparse category (say one
    # laptop under "shopping") could never be flagged at all.
    all_spends = df["spend"].to_numpy(dtype=float)
    g_median = float(np.median(all_spends))
    g_mad = float(np.median(np.abs(all_spends - g_median)))
    g_scale = g_mad * _MAD_SCALE if g_mad > 0 else float(all_spends.std(ddof=0))

    for category, group in df.groupby("category"):
        spends = group["spend"].to_numpy(dtype=float)
        median = float(np.median(spends))
        mad = float(np.median(np.abs(spends - median)))
        # Fall back to std if MAD collapses (many identical values).
        scale = mad * _MAD_SCALE if mad > 0 else float(spends.std(ddof=0))

        basis = "category"
        if len(spends) < _MIN_CATEGORY_COUNT or scale <= 0:
            # Too thin to judge locally -> compare against the whole statement.
            median, scale, basis = g_median, g_scale, "statement"

        category_stats[category] = {
            "count": int(len(spends)),
            "median_spend": round(float(np.median(spends)), 2),
            "basis": basis,
            "typical_range_high": round(median + _Z_THRESHOLD * scale, 2) if scale > 0 else None,
        }

        if scale <= 0:
            continue

        for _, row in group.iterrows():
            if row["is_subscription"]:
                continue  # accounted for by subscription detection / reconciliation
            z = (row["spend"] - median) / scale
            # Only large *over*-spends are interesting as anomalies.
            if z >= _Z_THRESHOLD:
                # ...and only if it is also unusual for this particular
                # merchant. A petrol fill is large for "transport" every single
                # time, which makes it a pattern rather than an outlier.
                if _routine_for_merchant(row["merchant"], row["spend"]):
                    routine_suppressed += 1
                    continue
                multiple = row["spend"] / median if median > 0 else float("inf")
                merchant_note = ""
                if row["merchant"] in merchant_stats:
                    m_med = merchant_stats[row["merchant"]][0]
                    if m_med > 0:
                        merchant_note = (
                            f" It is also {row['spend'] / m_med:.1f}x this "
                            f"merchant's usual ~{m_med:.0f}."
                        )
                anomalies.append({
                    "txn_date": str(row["txn_date"]),
                    "description": row["description"],
                    "amount": round(float(row["amount"]), 2),
                    "spend": round(float(row["spend"]), 2),
                    "category": category,
                    "z_score": round(float(z), 2),
                    "category_median": round(median, 2),
                    "explanation": (
                        f"{row['spend']:.0f} is {multiple:.1f}x the typical "
                        f"{category} spend (~{median:.0f}); robust z-score "
                        f"{z:.1f} exceeds {_Z_THRESHOLD}." + merchant_note
                    ),
                })

    anomalies.sort(key=lambda a: a["z_score"], reverse=True)

    return {
        "success": True,
        "method": "Robust per-category z-score (median + MAD)",
        "z_threshold": _Z_THRESHOLD,
        "total_transactions": int(len(df)),
        "subscription_transactions_excluded": int(df["is_subscription"].sum()),
        # Charges that cleared the category bar but are ordinary for their own
        # merchant. Reported rather than silently dropped, so the difference
        # between "found nothing" and "ruled these out" stays visible.
        "routine_for_merchant_suppressed": int(routine_suppressed),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "category_stats": category_stats,
    }
