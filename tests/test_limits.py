"""
Resource-exhaustion guards (QA finding: unbounded date span).

Against the pre-fix code a 3-row CSV with a mistyped year produced a
213,000-point daily series and a ~7.7 MB response, which OOM'd the live API.
"""
import json
import os

from core.forecast import forecast_cashflow, _MAX_ANALYSIS_DAYS, _MAX_DAILY_POINTS_RETURNED


def _db(tmp_path, csv_text, name="l.db"):
    from core.loader import load_csv_to_db
    p = os.path.join(tmp_path, "l.csv")
    with open(p, "w", newline="") as f:
        f.write(csv_text)
    dbp = os.path.join(tmp_path, name)
    return load_csv_to_db(p, dbp)[1], dbp


def test_implausible_dates_are_skipped_with_a_reason(tmp_path):
    info, _ = _db(tmp_path,
        "Date,Description,Amount\n"
        "1900-01-01,ANCIENT,-100\n"
        "2099-12-31,FUTURE,-100\n"
        "2024-01-01,GOOD,-50\n"
        "2024-02-01,GOOD2,-70\n")
    assert info["rows_skipped"] == 2
    reasons = " ".join(r["reason"] for r in info["skipped_rows"])
    assert "plausible range" in reasons
    assert "1900-01-01" in reasons and "2099-12-31" in reasons


def test_forecast_payload_stays_bounded_on_a_wide_span(tmp_path):
    """Even if wide-spanning rows survive, the response must stay small."""
    _, dbp = _db(tmp_path,
        "Date,Description,Amount\n"
        "1995-01-01,OLD,-100\n"
        "2024-01-01,A,-50\n"
        "2024-02-01,B,-70\n"
        "2024-03-01,C,-60\n", name="w.db")
    res = forecast_cashflow(dbp)
    assert res["success"]
    assert len(res["daily"]["history"]) <= _MAX_DAILY_POINTS_RETURNED
    payload_mb = len(json.dumps(res)) / 1024 / 1024
    assert payload_mb < 0.5, f"response ballooned to {payload_mb:.2f} MB"
    assert res["history_truncated"] is True


def test_normal_statement_is_not_truncated(tmp_path):
    _, dbp = _db(tmp_path,
        "Date,Description,Amount\n"
        "2024-01-01,A,-50\n2024-02-01,B,-70\n2024-03-01,C,-60\n", name="n.db")
    res = forecast_cashflow(dbp)
    assert res["success"]
    assert res["history_truncated"] is False
    assert res["history_days"] <= _MAX_ANALYSIS_DAYS
