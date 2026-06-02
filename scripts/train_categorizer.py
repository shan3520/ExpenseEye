"""
Train and persist the ExpenseEye transaction categorizer.

Pipeline: FeatureUnion(word TF-IDF [1-2 gram] + char TF-IDF [3-5 gram])
          -> LogisticRegression.

Evaluates on a stratified held-out split and writes:
  * models/category_clf.joblib  - the fitted pipeline (trained on ALL data)
  * models/model_card.json      - accuracy, macro precision/recall/F1,
                                  per-class report and confusion matrix.

Run:  python scripts/train_categorizer.py

Copyright (c) 2026 Shantanu (shan3520) - MIT License
"""

import json
import os

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, precision_recall_fscore_support)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_PATH = os.path.join(ROOT, "data", "seed_transactions.csv")
MODEL_PATH = os.path.join(ROOT, "models", "category_clf.joblib")
MODEL_CARD_PATH = os.path.join(ROOT, "models", "model_card.json")


def build_pipeline():
    """TF-IDF word + char n-grams -> LogisticRegression."""
    word_vec = TfidfVectorizer(
        analyzer="word", ngram_range=(1, 2), min_df=1, sublinear_tf=True,
        lowercase=True, token_pattern=r"(?u)\b\w+\b",
    )
    char_vec = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True,
        lowercase=True,
    )
    features = FeatureUnion([("word", word_vec), ("char", char_vec)])
    clf = LogisticRegression(max_iter=2000, C=10.0, class_weight="balanced")
    return Pipeline([("features", features), ("clf", clf)])


def main():
    if not os.path.exists(SEED_PATH):
        raise SystemExit(
            f"Seed data not found at {SEED_PATH}. "
            f"Run: python scripts/generate_data.py"
        )

    df = pd.read_csv(SEED_PATH)
    X = df["description"].astype(str)
    y = df["category"].astype(str)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    pipe = build_pipeline()
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    p, r, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="macro", zero_division=0
    )
    labels = sorted(y.unique())
    report = classification_report(
        y_test, y_pred, zero_division=0, output_dict=True
    )
    cm = confusion_matrix(y_test, y_pred, labels=labels).tolist()

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    # Persist the model trained on ALL data (more data -> better in production);
    # the reported metrics come from the held-out split above.
    final = build_pipeline().fit(X, y)
    import joblib
    joblib.dump(final, MODEL_PATH)

    card = {
        "model": "TF-IDF (word 1-2gram + char 3-5gram) + LogisticRegression",
        "n_samples": int(len(df)),
        "n_classes": int(len(labels)),
        "classes": labels,
        "test_size": 0.25,
        "metrics": {
            "accuracy": round(float(accuracy), 4),
            "macro_precision": round(float(p), 4),
            "macro_recall": round(float(r), 4),
            "macro_f1": round(float(f1), 4),
        },
        "per_class": {
            k: {
                "precision": round(v["precision"], 4),
                "recall": round(v["recall"], 4),
                "f1": round(v["f1-score"], 4),
                "support": int(v["support"]),
            }
            for k, v in report.items()
            if k in labels
        },
        "confusion_matrix": {"labels": labels, "matrix": cm},
    }
    with open(MODEL_CARD_PATH, "w", encoding="utf-8") as f:
        json.dump(card, f, indent=2)

    print(f"Saved model      -> {MODEL_PATH}")
    print(f"Saved model card -> {MODEL_CARD_PATH}")
    print(f"Accuracy={accuracy:.4f}  macro-P={p:.4f}  macro-R={r:.4f}  macro-F1={f1:.4f}")


if __name__ == "__main__":
    main()
