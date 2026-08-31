"""
Legacy convenience loader.

The real, schema-flexible parser lives in core/loader.py; this thin wrapper
just loads a sample statement into a local SQLite DB for quick manual
inspection. (Previously hard-coded to a real bank export that has since been
removed from the repo for privacy — see remediation brief P1-11.)
"""
import sqlite3

from core.loader import load_csv_to_db

CSV = "data/sample_statement_iso.csv"
DB = "smartspend.db"

print(f"Loading {CSV} -> {DB} ...")
n, mapping = load_csv_to_db(CSV, DB)
print(f"Inserted {n} transactions. Mapping: {mapping}")

conn = sqlite3.connect(DB)
try:
    print("\nFirst 5 rows:")
    for row in conn.execute("SELECT * FROM transactions LIMIT 5"):
        print(f"  ID {row[0]} | {row[1]} | {row[2]} | {row[3]}")
finally:
    conn.close()
print("\nDone.")
