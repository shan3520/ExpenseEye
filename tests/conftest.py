"""
Shared pytest fixtures for ExpenseEye.

Adds the repo root to sys.path so `import core.*` / `import api.*` work when
pytest is run from anywhere, and exposes a `load_csv` helper that drives the
real loader end-to-end (CSV text or file -> session DB -> rows).
"""
import os
import sqlite3
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture
def load_csv(tmp_path):
    """
    Load CSV text (or an existing file path when is_path=True) through the real
    loader and return (rows_loaded, mapping_info, rows), where rows is a list of
    (txn_date, description, amount) tuples ordered by insertion.
    """
    from core.loader import load_csv_to_db

    def _load(text_or_path, is_path=False):
        if is_path:
            csv_path = text_or_path
        else:
            csv_path = os.path.join(tmp_path, "in.csv")
            with open(csv_path, "w", newline="") as f:
                f.write(text_or_path)
        db_path = os.path.join(tmp_path, "out.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        n, info = load_csv_to_db(csv_path, db_path)
        con = sqlite3.connect(db_path)
        try:
            rows = con.execute(
                "SELECT txn_date, description, amount FROM transactions ORDER BY id"
            ).fetchall()
        finally:
            con.close()
        return n, info, rows

    return _load
