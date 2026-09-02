"""
ExpenseEye ML Transaction Categorizer.

Copyright (c) 2026 Shantanu (shan3520)
Original Repository: https://github.com/shan3520/expenseeye
License: MIT

Replaces rule-based categorization with a trained text classifier:
  * Features : TF-IDF over word (1-2 gram) AND character (3-5 gram) n-grams,
               combined with a FeatureUnion. Char n-grams make it robust to
               the abbreviations / typos common in bank descriptions.
  * Model    : LogisticRegression (well-calibrated probabilities for the
               confidence-based fallback).
  * Fallback : rule-based keyword matching is used ONLY when the model's
               confidence is below a threshold, so the legacy behaviour still
               backs up uncertain predictions.

The model is trained once (see scripts/train_categorizer.py) and persisted to
models/category_clf.joblib. It is loaded lazily and cached at module level, so
it is never retrained or reloaded per request.
"""

import re
import json
import os
import sqlite3
import threading

import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(_ROOT, "models", "category_clf.joblib")
MODEL_CARD_PATH = os.path.join(_ROOT, "models", "model_card.json")
SEED_PATH = os.path.join(_ROOT, "data", "seed_transactions.csv")

# Below this max-class probability we defer to the rule-based fallback.
CONFIDENCE_THRESHOLD = 0.45

_model = None
_model_lock = threading.Lock()

# Keyword rules used as a low-confidence fallback (and to bootstrap if the
# trained model is unavailable at runtime).
# NOTE: matched as substrings, first category wins (see _rule_category). Keep
# keys specific enough not to collide — e.g. bare "jio" is intentionally absent
# because it would swallow JIOMART (groceries) and JIOHOTSTAR (subscriptions).
_RULES = {
    "income": ["salary", "payroll", "dividend", "interest credit", "freelance",
               "consulting", "stipend", "sbint", "int cr", "interest paid"],
    "rent": ["rent", "landlord", "accommodation", "maintenance charge", "society charge"],
    "subscriptions": ["netflix", "spotify", "prime", "disney", "youtube", "icloud",
                      "adobe", "hotstar", "jiohotstar", "jiocinema", "sonyliv", "zee5",
                      "audible", "gym", "cult fit", "cultfit", "linkedin", "365", "hbo"],
    "utilities": ["electric", "electricity", "water bill", "gas bill", "broadband",
                  "internet", "fibernet", "jio fiber", "jiofiber", "act fibernet",
                  "airtel", "vodafone", "bescom", "tata power", "adani electricity",
                  "mahanagar gas", "comcast", "xfinity", "at&t", "wireless",
                  "postpaid", "utility", "jioinapp", "prepaid recharge",
                  "mobile recharge", "dth"],
    "transport": ["uber", "ola", "rapido", "namma yatri", "nammayatri", "indrive",
                  "lyft", "fuel", "petrol", "diesel", "metro", "irctc", "redbus",
                  "bmtc", "bus pass", "indigo", "spicejet", "vistara", "akasa",
                  "makemytrip", "ixigo", "parking", "fastag", "oil"],
    "dining": ["starbucks", "mcdonald", "domino", "kfc", "subway", "chipotle", "swiggy",
               "zomato", "eats", "doordash", "taco", "dunkin", "pizza", "cafe", "coffee",
               "haldiram", "behrouz", "faasos", "restaurant", "biryani", "panera"],
    "groceries": ["grocery", "groceries", "foods", "blinkit", "zepto", "instamart",
                  "bigbasket", "jiomart", "country delight", "licious", "supermarket",
                  "trader joe", "safeway", "aldi", "kroger", "bazaar", "dmart",
                  "reliance fresh", "tesco", "costco", "sprouts", "lidl", "publix"],
    "shopping": ["amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa", "tata neu",
                 "reliance digital", "urban company", "best buy", "target", "ikea",
                 "nike", "h&m", "zara", "decathlon", "croma", "apple store", "ebay"],
    "transfers": ["upi", "neft", "imps", "rtgs", "paytm", "phonepe", "gpay", "venmo",
                  "zelle", "transfer", "google pay", "cheque", "chq", "ecs", "nach",
                  "funds transfer"],
    # Cash leaves the account and the statement stops being able to see it. That
    # is worth saying plainly rather than filing under "uncategorized", which
    # reads as a failure to classify rather than a limit of the data.
    "cash": ["atm", "cash withdrawal", "cash wdl", "cash dep"],
    "fees": ["sms charges", "debit card annual", "stock chrg", "annual fee",
             "service charge", "penalty", "late fee", "amc", "processing fee",
             "convenience fee", "gst on", "chrg"],
}


def _compile(keywords):
    """Prefix-anchored patterns: a word boundary on the LEFT only.

    Bare substring matching let "atm" fire inside "BATMAN" and "TREATMENT". A
    boundary on BOTH sides fixes that but breaks the far more common case, since
    banks truncate merchant names -- "DOMINOSP", "AMAZONPA", "FLIPKART" -- and a
    trailing boundary refuses to match any of them.

    Anchoring the start only keeps both properties: "domino" matches
    "DOMINOSP", while "atm" cannot match "BATMAN", where "atm" is preceded by
    a word character. The boundary is omitted when a keyword does not begin with
    a word character, so "h&m" and "at&t" still match."""
    parts = []
    for kw in keywords:
        esc = re.escape(kw)
        left = r"\b" if kw[:1].isalnum() else ""
        parts.append(left + esc)
    return re.compile("|".join(parts), re.IGNORECASE)


_RULE_PATTERNS = {cat: _compile(kws) for cat, kws in _RULES.items()}


def _rule_category(description):
    """Best-effort keyword match. Returns a category or 'uncategorized'.

    Order matters and is the order of _RULES: merchant categories are tested
    before "transfers", so "UPI SWIGGY" is dining rather than a transfer, while
    a bare "UPI <person>" falls through to transfers."""
    text = str(description)
    for category, pattern in _RULE_PATTERNS.items():
        if pattern.search(text):
            return category
    return "uncategorized"


def _get_model():
    """Load and cache the persisted model. Returns None if unavailable."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None and os.path.exists(MODEL_PATH):
            import joblib
            _model = joblib.load(MODEL_PATH)
    return _model


def predict_categories(descriptions):
    """
    Categorize descriptions the one way the whole app should.

    Returns a list of (category, confidence, source) triples. A model
    prediction below CONFIDENCE_THRESHOLD falls back to the rule table.

    This exists because anomaly detection used to call model.predict() raw
    while this module applied the threshold and the fallback. The two then
    disagreed about the SAME transaction -- one card called a large Amazon
    charge "shopping" and another called it "subscriptions" -- and, worse, the
    anomaly z-score was measured against the wrong category's baseline.
    """
    descriptions = [str(d) for d in descriptions]
    if not descriptions:
        return []

    model = _get_model()
    if model is None:
        # Model unavailable -> pure rule-based so the feature still works.
        return [(_rule_category(d), None, "rule_fallback") for d in descriptions]

    proba = model.predict_proba(descriptions)
    classes = model.classes_
    top_idx = proba.argmax(axis=1)

    out = []
    for i, desc in enumerate(descriptions):
        confidence = float(proba[i, top_idx[i]])
        if confidence >= CONFIDENCE_THRESHOLD:
            out.append((str(classes[top_idx[i]]), confidence, "model"))
        else:
            out.append((_rule_category(desc), confidence, "rule_fallback"))
    return out


def categorize_transactions(db_path):
    """
    Categorize every transaction in a session database.

    Returns a JSON-serializable dict with per-transaction predictions, a
    category breakdown, and how many predictions came from the model vs. the
    rule-based fallback.
    """
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(
            "SELECT txn_date, description, amount FROM transactions ORDER BY txn_date",
            conn,
        )
    finally:
        conn.close()

    if df.empty:
        return {"success": False, "error": "No transactions to categorize."}

    descriptions = df["description"].fillna("").astype(str).tolist()

    results = []
    model_used = 0
    rule_used = 0

    for i, (category, confidence, source) in enumerate(predict_categories(descriptions)):
        if source == "model":
            model_used += 1
        else:
            rule_used += 1
        results.append({
            "description": descriptions[i],
            "amount": float(df.iloc[i]["amount"]),
            "category": category,
            "confidence": round(confidence, 3) if confidence is not None else None,
            "source": source,
        })

    # Spending breakdown per category (expenses only, as positive spend).
    breakdown = {}
    for r in results:
        if r["amount"] < 0:
            breakdown[r["category"]] = breakdown.get(r["category"], 0.0) + abs(r["amount"])
    breakdown = [
        {"category": k, "total_spend": round(v, 2)}
        for k, v in sorted(breakdown.items(), key=lambda kv: -kv[1])
    ]

    return {
        "success": True,
        "model_available": _get_model() is not None,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "counts": {
            "total": len(results),
            "model": model_used,
            "rule_fallback": rule_used,
        },
        "breakdown": breakdown,
        "transactions": results,
    }


def get_model_card():
    """Return the persisted evaluation metrics ('model card')."""
    if os.path.exists(MODEL_CARD_PATH):
        with open(MODEL_CARD_PATH, "r", encoding="utf-8") as f:
            card = json.load(f)
        card["success"] = True
        card["model_available"] = os.path.exists(MODEL_PATH)
        return card
    return {
        "success": False,
        "model_available": os.path.exists(MODEL_PATH),
        "error": "Model card not found. Train the model first "
                 "(python scripts/train_categorizer.py).",
    }
