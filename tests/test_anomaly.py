"""
Anomaly detection must not contradict subscription detection (brief P2-15).
"""
import os

from core.loader import load_csv_to_db
from core.subscriptions import detect_subscriptions, normalize_description
from core.anomaly import detect_anomalies

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def test_detected_subscriptions_are_not_flagged_as_anomalies(tmp_path):
    dbp = os.path.join(tmp_path, "a.db")
    load_csv_to_db(os.path.join(DATA, "sample_statement_iso.csv"), dbp)

    sub_keys = {normalize_description(s["description"]) for s in detect_subscriptions(dbp)}
    assert sub_keys, "fixture should contain subscriptions"

    res = detect_anomalies(dbp)
    assert res["success"]
    flagged = {normalize_description(a["description"]) for a in res["anomalies"]}
    # No merchant identified as a subscription may also be an "anomaly".
    assert flagged.isdisjoint(sub_keys)
