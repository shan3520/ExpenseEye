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


def test_large_outlier_still_flagged_on_subscription_heavy_statement(tmp_path):
    """Excluding subscriptions from candidacy must not gut the population:
    a one-off large charge in a thin category still has to be flagged, judged
    against the statement-wide baseline."""
    dbp = os.path.join(tmp_path, "b.db")
    load_csv_to_db(os.path.join(DATA, "sample_statement_iso.csv"), dbp)
    res = detect_anomalies(dbp)
    assert res["success"]
    flagged = {a["description"].upper() for a in res["anomalies"]}
    assert any("MACBOOK" in d for d in flagged), (
        "the single largest one-off charge must be flagged even though the "
        "statement is dominated by recurring subscriptions"
    )
    # And it must still not contradict subscription detection.
    sub_keys = {normalize_description(s["description"]) for s in detect_subscriptions(dbp)}
    assert {normalize_description(a["description"]) for a in res["anomalies"]}.isdisjoint(sub_keys)
