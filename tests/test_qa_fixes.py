"""
Regression tests for the second-round QA findings.

Each of these fails against the code as it stood before that QA pass.
"""
import os

import pytest

from core.loader import load_csv_to_db, sniff_delimiter
from core.subscriptions import detect_subscriptions
from core.overspending import detect_overspending

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _load(tmp_path, text, name="d"):
    p = os.path.join(tmp_path, f"{name}.csv")
    with open(p, "w", newline="") as f:
        f.write(text)
    dbp = os.path.join(tmp_path, f"{name}.db")
    return load_csv_to_db(p, dbp), dbp


# ---------------------------------------------------------------- delimiters #
@pytest.mark.parametrize("sep", [";", "\t", "|", ","])
def test_non_comma_delimiters_are_detected(tmp_path, sep):
    text = (f"Date{sep}Description{sep}Amount\n"
            f"2024-01-01{sep}ONE{sep}-100\n"
            f"2024-02-01{sep}TWO{sep}-50\n")
    (n, info), _ = _load(tmp_path, text, name=f"sep{ord(sep)}")
    assert n == 2, f"delimiter {sep!r} not handled"
    assert info["rows_skipped"] == 0


def test_sniff_delimiter_prefers_the_consistent_one(tmp_path):
    p = os.path.join(tmp_path, "s.csv")
    with open(p, "w", newline="") as f:
        f.write("Date;Description;Amount\n2024-01-01;A, INC;-100\n")
    assert sniff_delimiter(p) == ";"


# ------------------------------------------------------------ header picking #
def test_header_detection_does_not_match_a_data_row(tmp_path):
    """The generic keyword 'value' used to match the data cell 'value1', so a
    data row became the header and the error quoted a value as a column."""
    with pytest.raises(ValueError, match="JustOneColumn"):
        _load(tmp_path, "JustOneColumn\nvalue1\nvalue2\n", name="one")


# -------------------------------------------------- subscription precision  #
def test_irregular_repeat_purchases_are_not_subscriptions(tmp_path):
    """Three trips to a shop 103 and 78 days apart are not a quarterly
    subscription; the absolute dispersion bound must reject them."""
    text = ("Date,Description,Amount\n"
            "2023-01-10,PUBLIX,-1394.66\n"
            "2023-04-23,PUBLIX,-1573.82\n"
            "2023-07-10,PUBLIX,-1623.82\n")
    _, dbp = _load(tmp_path, text, name="pub")
    assert detect_subscriptions(dbp) == []


def test_genuine_monthly_series_still_detected(tmp_path):
    """Precision must not cost recall: a real monthly bill is still found."""
    rows = "".join(f"2023-{m:02d}-18,AIRTEL POSTPAID,-2500\n" for m in range(1, 7))
    _, dbp = _load(tmp_path, "Date,Description,Amount\n" + rows, name="air")
    subs = detect_subscriptions(dbp)
    assert len(subs) == 1
    assert subs[0]["frequency"] == "MONTHLY"


def test_iso_fixture_recall_unchanged(tmp_path):
    """The five monthly series in the shipped fixture must still be detected."""
    dbp = os.path.join(tmp_path, "iso.db")
    load_csv_to_db(os.path.join(DATA, "sample_statement_iso.csv"), dbp)
    subs = detect_subscriptions(dbp)
    assert len(subs) == 5
    assert all(s["frequency"] == "MONTHLY" and s["occurrences"] == 12 for s in subs)


# ------------------------------------------------------------- overspending #
def test_overspending_requires_material_and_statistical_deviation(tmp_path):
    """A month barely above a trailing baseline is not overspending. The old
    rule ORed 20% with 1-sigma, so 1-sigma always fired and 53% of months on
    the shipped sample were flagged, some as low as +9.7%."""
    dbp = os.path.join(tmp_path, "os.db")
    load_csv_to_db(os.path.join(DATA, "sample_statement.csv"), dbp)
    res = detect_overspending(dbp)
    flagged = [r for r in res if r["status"] == "OVERSPENDING"]
    assert len(flagged) / len(res) < 0.25, "detector still fires on too much of its input"
    for r in flagged:
        assert r["pct_deviation"] >= 20.0
        assert r["z_score"] >= 2.0


def test_a_genuine_spike_is_still_flagged(tmp_path):
    """Precision must not make the detector inert."""
    rows = "".join(f"2023-{m:02d}-05,RENT,-20000\n" for m in range(1, 9))
    rows += "2023-09-05,RENT,-20000\n2023-09-06,LAPTOP,-250000\n"
    _, dbp = _load(tmp_path, "Date,Description,Amount\n" + rows, name="spike")
    res = detect_overspending(dbp)
    assert any(r["status"] == "OVERSPENDING" for r in res)
