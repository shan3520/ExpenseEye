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

from core.categorizer import _rule_category, _get_model

# A transaction is flagged when its robust z-score exceeds this threshold.
_Z_THRESHOLD = 3.5
# Categories need at least this many transactions before we judge outliers.
_MIN_CATEGORY_COUNT = 5
# MAD -> std-dev consistency constant for normally distributed data.
_MAD_SCALE = 1.4826


def _category_for(descriptions):
    """Categorize descriptions with the ML model if present, else rules."""
    model = _get_model()
    if model is not None:
        return [str(c) for c in model.predict(list(descriptions))]
    return [_rule_category(d) for d in descriptions]


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

    df["spend"] = df["amount"].abs()
    df["category"] = _category_for(df["description"].fillna("").astype(str))

    anomalies = []
    category_stats = {}

    for category, group in df.groupby("category"):
        spends = group["spend"].to_numpy(dtype=float)
        median = float(np.median(spends))
        mad = float(np.median(np.abs(spends - median)))
        # Fall back to std if MAD collapses (many identical values).
        scale = mad * _MAD_SCALE if mad > 0 else float(spends.std(ddof=0))
        category_stats[category] = {
            "count": int(len(spends)),
            "median_spend": round(median, 2),
            "typical_range_high": round(median + _Z_THRESHOLD * scale, 2) if scale > 0 else None,
        }

        if len(spends) < _MIN_CATEGORY_COUNT or scale <= 0:
            continue

        for _, row in group.iterrows():
            z = (row["spend"] - median) / scale
            # Only large *over*-spends are interesting as anomalies.
            if z >= _Z_THRESHOLD:
                multiple = row["spend"] / median if median > 0 else float("inf")
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
                        f"{z:.1f} exceeds {_Z_THRESHOLD}."
                    ),
                })

    anomalies.sort(key=lambda a: a["z_score"], reverse=True)

    return {
        "success": True,
        "method": "Robust per-category z-score (median + MAD)",
        "z_threshold": _Z_THRESHOLD,
        "total_transactions": int(len(df)),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "category_stats": category_stats,
    }
