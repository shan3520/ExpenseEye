"""
Reconciliation loop tests (Track 04: match rate + honest exception list).

Verifies the loop reports a match rate over the whole expected batch and
surfaces BOTH sides of the exception list — a charge that never landed, and a
charge that no expected occurrence accounts for.
"""
import csv
import os

import pytest

from core.loader import load_csv_to_db
from core.reconcile import reconcile_recurring

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
FIXTURE = os.path.join(DATA, "sample_statement_iso.csv")


def _db(tmp_path, csv_path, name="r.db"):
    dbp = os.path.join(tmp_path, name)
    load_csv_to_db(csv_path, dbp)
    return dbp


def test_clean_statement_reconciles_fully(tmp_path):
    """The ISO fixture bills 5 series every month with no gaps, so every
    expected occurrence must be accounted for."""
    res = reconcile_recurring(_db(tmp_path, FIXTURE))
    assert res["success"]
    s = res["summary"]
    assert s["expected_occurrences"] == 60
    assert s["match_rate"] == 100.0
    assert s["missing"] == 0 and s["unscheduled"] == 0


def test_missing_and_unscheduled_charges_are_caught(tmp_path):
    """Remove one scheduled charge and inject one off-cycle charge; the loop
    must report exactly those two exceptions and nothing else."""
    rows = list(csv.reader(open(FIXTURE)))
    hdr, body = rows[0], rows[1:]
    body = [r for r in body
            if not (r[1].startswith("NETFLIX") and r[0].startswith("2023-06"))]
    body.append(["2023-07-19", "SPOTIFY PREMIUM", "DR", "119.00", "0.00"])
    tampered = os.path.join(tmp_path, "tampered.csv")
    with open(tampered, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(hdr)
        w.writerows(sorted(body, key=lambda r: r[0]))

    res = reconcile_recurring(_db(tmp_path, tampered, "t.db"))
    assert res["success"]
    s = res["summary"]
    assert s["missing"] == 1
    assert s["unscheduled"] == 1
    assert s["match_rate"] < 100.0

    miss = res["exceptions"]["missing"][0]
    assert "NETFLIX" in miss["merchant"].upper()
    assert miss["expected_date"].startswith("2023-06")

    extra = res["exceptions"]["unscheduled"][0]
    assert "SPOTIFY" in extra["merchant"].upper()
    assert extra["txn_date"] == "2023-07-19"


def test_every_expected_occurrence_is_accounted_for(tmp_path):
    """No cherry-picking: matched + missing must equal the expected total."""
    res = reconcile_recurring(_db(tmp_path, FIXTURE))
    s = res["summary"]
    assert s["matched"] + s["missing"] == s["expected_occurrences"]
    assert s["matched_clean"] + s["matched_with_variance"] == s["matched"]


def test_no_recurring_series_reports_cleanly(tmp_path):
    """A statement with nothing recurring must fail soft, not crash."""
    p = os.path.join(tmp_path, "flat.csv")
    with open(p, "w", newline="") as f:
        f.write("Date,Description,Amount\n2024-01-01,ONE OFF SHOP,-100\n"
                "2024-02-14,ANOTHER SHOP,-250\n2024-03-09,THIRD SHOP,-75\n")
    res = reconcile_recurring(_db(tmp_path, p, "f.db"))
    assert res["success"] is False
    assert "recurring" in res["error"].lower()
