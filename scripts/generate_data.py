"""
Generate realistic, reproducible sample data for ExpenseEye's ML features.

Produces two artifacts:
  * data/seed_transactions.csv  - labeled (description -> category) training data
                                   for the ML transaction categorizer.
  * data/sample_statement.csv   - an 18-month bank statement with genuine
                                   recurring structure (salary, rent, subs,
                                   groceries, transport, ...) so the cash-flow
                                   forecast can demonstrate real predictive
                                   skill instead of fitting noise.

Run:  python scripts/generate_data.py
Deterministic via a fixed RNG seed so metrics are reproducible.

Copyright (c) 2026 Shantanu (shan3520) - MIT License
"""

import csv
import os
import random
from datetime import date, timedelta

RNG = random.Random(42)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

# --------------------------------------------------------------------------- #
# Merchant vocabulary per category. Used for BOTH the labeled seed data and
# the synthetic statement, so the categorizer sees realistic descriptions.
# --------------------------------------------------------------------------- #
MERCHANTS = {
    "groceries": [
        "WALMART GROCERY", "WHOLE FOODS MKT", "TRADER JOES", "SAFEWAY STORE",
        "ALDI", "KROGER", "BIG BAZAAR", "DMART", "RELIANCE FRESH", "TESCO",
        "COSTCO WHOLESALE", "SPROUTS FARMERS MKT", "LIDL", "PUBLIX",
    ],
    "dining": [
        "STARBUCKS", "MCDONALDS", "DOMINOS PIZZA", "KFC", "SUBWAY", "CHIPOTLE",
        "SWIGGY ORDER", "ZOMATO", "UBER EATS", "DOORDASH", "TACO BELL",
        "DUNKIN", "PIZZA HUT", "CAFE COFFEE DAY", "PANERA BREAD",
    ],
    "transport": [
        "UBER TRIP", "OLA CABS", "LYFT RIDE", "SHELL FUEL", "BP PETROL",
        "INDIAN OIL", "METRO CARD RECHARGE", "IRCTC TRAIN", "REDBUS",
        "PARKING FEE", "HP PETROL PUMP", "FASTAG RECHARGE", "DELHI METRO",
    ],
    "utilities": [
        "ELECTRIC BILL PAYMENT", "WATER UTILITY", "GAS BILL", "BROADBAND INTERNET",
        "AIRTEL POSTPAID", "JIO RECHARGE", "VODAFONE BILL", "COMCAST XFINITY",
        "AT&T WIRELESS", "ELECTRICITY BOARD", "MUNICIPAL WATER TAX",
    ],
    "subscriptions": [
        "NETFLIX", "SPOTIFY PREMIUM", "AMAZON PRIME", "DISNEY PLUS", "YOUTUBE PREMIUM",
        "ICLOUD STORAGE", "ADOBE CREATIVE CLOUD", "HOTSTAR", "AUDIBLE", "GYM MEMBERSHIP",
        "LINKEDIN PREMIUM", "MICROSOFT 365", "HBO MAX",
    ],
    "shopping": [
        "AMAZON ORDER", "FLIPKART", "MYNTRA", "AJIO", "BEST BUY", "TARGET",
        "IKEA", "NIKE STORE", "H&M", "ZARA", "DECATHLON", "CROMA ELECTRONICS",
        "APPLE STORE", "EBAY PURCHASE",
    ],
    "rent": [
        "MONTHLY RENT PAYMENT", "APARTMENT RENT", "HOUSE RENT TRANSFER",
        "LANDLORD RENT", "PG ACCOMMODATION RENT",
    ],
    "income": [
        "SALARY CREDIT", "PAYROLL DEPOSIT", "MONTHLY SALARY", "ACME CORP SALARY",
        "FREELANCE PAYMENT", "CONSULTING INCOME", "INTEREST CREDIT", "DIVIDEND PAYOUT",
    ],
    "transfers": [
        "UPI TRANSFER", "NEFT TRANSFER", "IMPS PAYMENT", "PAYTM WALLET",
        "VENMO PAYMENT", "ZELLE TRANSFER", "ACCOUNT TRANSFER", "GOOGLE PAY SENT",
    ],
}


def _write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


# --------------------------------------------------------------------------- #
# 1) Labeled seed data for the categorizer
# --------------------------------------------------------------------------- #
def build_seed(per_category=45):
    """~45 descriptions per category with light realistic noise/suffixes."""
    suffixes = ["", " #{}", " TXN{}", " REF {}", " *{}", " - CARD", " POS",
                " ONLINE", " STORE {}", " PMT"]
    rows = []
    for category, merchants in MERCHANTS.items():
        for _ in range(per_category):
            base = RNG.choice(merchants)
            suf = RNG.choice(suffixes)
            if "{}" in suf:
                suf = suf.format(RNG.randint(100, 9999))
            desc = (base + suf).strip()
            rows.append([desc, category])
    RNG.shuffle(rows)
    _write_csv(os.path.join(DATA_DIR, "seed_transactions.csv"),
               ["description", "category"], rows)
    return len(rows)


# --------------------------------------------------------------------------- #
# 2) Realistic 18-month bank statement with recurring structure + trend
# --------------------------------------------------------------------------- #
def build_statement(months=18):
    start = date(2023, 1, 1)
    rows = []  # date, description, amount (signed: negative=spend, positive=income)

    def add(d, category, amount):
        desc = RNG.choice(MERCHANTS[category])
        # Sample data uses DD/MM/YYYY. The loader also handles ISO YYYY-MM-DD
        # and MM/DD/YYYY — see core.loader.detect_date_format.
        rows.append([d.strftime("%d/%m/%Y"), desc, round(amount, 2)])

    for m in range(months):
        year = start.year + (start.month - 1 + m) // 12
        month = (start.month - 1 + m) % 12 + 1
        first = date(year, month, 1)
        # mild inflation/lifestyle creep so there is a learnable upward trend
        trend = 1.0 + 0.012 * m

        # --- fixed recurring (very predictable) ---
        add(date(year, month, 1), "income", 85000 * trend + RNG.gauss(0, 800))   # salary
        add(date(year, month, 3), "rent", -(22000 * trend + RNG.gauss(0, 150)))  # rent
        # subscriptions on fixed days
        for day, amt in [(5, 499), (8, 199), (12, 1499), (15, 650)]:
            add(date(year, month, day), "subscriptions", -(amt + RNG.gauss(0, 10)) * trend)
        # utilities mid-month
        add(date(year, month, 18), "utilities", -(2400 * trend + RNG.gauss(0, 200)))

        # --- weekly groceries (4-5 per month) ---
        for wk in range(4):
            day = min(28, 2 + wk * 7 + RNG.randint(0, 2))
            add(date(year, month, day), "groceries", -(1800 * trend + RNG.gauss(0, 250)))

        # --- frequent small spend: dining + transport (semi-regular) ---
        for _ in range(RNG.randint(8, 12)):
            day = RNG.randint(1, 28)
            add(date(year, month, day), "dining", -(350 * trend + abs(RNG.gauss(0, 120))))
        for _ in range(RNG.randint(6, 10)):
            day = RNG.randint(1, 28)
            add(date(year, month, day), "transport", -(180 * trend + abs(RNG.gauss(0, 90))))

        # --- occasional shopping (bursty but bounded) ---
        for _ in range(RNG.randint(2, 5)):
            day = RNG.randint(1, 28)
            add(date(year, month, day), "shopping", -(1500 * trend + abs(RNG.gauss(0, 900))))

        # --- a couple of transfers ---
        for _ in range(RNG.randint(1, 3)):
            day = RNG.randint(1, 28)
            add(date(year, month, day), "transfers", -(2000 + abs(RNG.gauss(0, 1500))))

    rows.sort(key=lambda r: tuple(reversed(r[0].split("/"))))  # by YYYY,MM,DD
    _write_csv(os.path.join(DATA_DIR, "sample_statement.csv"),
               ["Date", "Description", "Amount"], rows)
    return len(rows)


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    n_seed = build_seed()
    n_stmt = build_statement()
    print(f"Wrote data/seed_transactions.csv  ({n_seed} labeled rows)")
    print(f"Wrote data/sample_statement.csv   ({n_stmt} transactions)")
