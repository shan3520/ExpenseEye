"""
Subscription detection regression tests (remediation brief P0-3, P2-16).

Against the audited HEAD, `test_drifting_monthly_subscription_detected` fails:
grouping on exact float amount put each drifting month in its own group, so a
real subscription whose price moves was never detected.
"""
import os
import sqlite3

from core.loader import load_csv_to_db
from core.subscriptions import detect_subscriptions

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _load(tmp_path, csv_path):
    dbp = os.path.join(tmp_path, "s.db")
    load_csv_to_db(csv_path, dbp)
    return dbp


def test_drifting_monthly_subscription_detected(tmp_path):
    # The ISO fixture bills NETFLIX every month with the amount drifting ~±5%.
    dbp = _load(tmp_path, os.path.join(DATA, "sample_statement_iso.csv"))
    subs = detect_subscriptions(dbp)
    netflix = [s for s in subs if "NETFLIX" in s["description"].upper()]
    assert len(netflix) == 1, "drifting monthly charge should be ONE subscription"
    assert netflix[0]["frequency"] == "MONTHLY"
    assert netflix[0]["occurrences"] == 12
    # The price drift is disclosed as a min/max range.
    assert netflix[0]["amount_min"] != netflix[0]["amount_max"]


def test_detection_is_pure_no_db_writes(tmp_path):
    # P2-16: a GET-backed read must not mutate the session database.
    dbp = _load(tmp_path, os.path.join(DATA, "sample_statement_iso.csv"))
    detect_subscriptions(dbp)
    con = sqlite3.connect(dbp)
    try:
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
    finally:
        con.close()
    assert "subscriptions" not in tables
