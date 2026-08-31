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
               "consulting", "stipend"],
    "rent": ["rent", "landlord", "accommodation", "maintenance charge", "society charge"],
    "subscriptions": ["netflix", "spotify", "prime", "disney", "youtube", "icloud",
                      "adobe", "hotstar", "jiohotstar", "jiocinema", "sonyliv", "zee5",
                      "audible", "gym", "cult fit", "cultfit", "linkedin", "365", "hbo"],
    "utilities": ["electric", "electricity", "water bill", "gas bill", "broadband",
                  "internet", "fibernet", "jio fiber", "jiofiber", "act fibernet",
                  "airtel", "vodafone", "bescom", "tata power", "adani electricity",
                  "mahanagar gas", "comcast", "xfinity", "at&t", "wireless",
                  "postpaid", "utility"],
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
                  "zelle", "transfer", "google pay"],
}


def _rule_category(description):
    """Best-effort keyword match. Returns a category or 'uncategorized'."""
    text = str(description).lower()
    for category, keywords in _RULES.items():
        if any(kw in text for kw in keywords):
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
    model = _get_model()

    results = []
    model_used = 0
    rule_used = 0

    if model is not None:
        import numpy as np
        proba = model.predict_proba(descriptions)
        classes = model.classes_
        top_idx = proba.argmax(axis=1)
        for i, desc in enumerate(descriptions):
            confidence = float(proba[i, top_idx[i]])
            if confidence >= CONFIDENCE_THRESHOLD:
                category = str(classes[top_idx[i]])
                source = "model"
                model_used += 1
            else:
                category = _rule_category(desc)
                source = "rule_fallback"
                rule_used += 1
            results.append({
                "description": desc,
                "amount": float(df.iloc[i]["amount"]),
                "category": category,
                "confidence": round(confidence, 3),
                "source": source,
            })
    else:
        # Model unavailable -> pure rule-based so the feature still works.
        for i, desc in enumerate(descriptions):
            results.append({
                "description": desc,
                "amount": float(df.iloc[i]["amount"]),
                "category": _rule_category(desc),
                "confidence": None,
                "source": "rule_fallback",
            })
            rule_used += 1

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
        "model_available": model is not None,
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
