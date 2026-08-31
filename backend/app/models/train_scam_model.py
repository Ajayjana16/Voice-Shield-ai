"""
Training script for Voice Shield Scam vs Non-Scam NLP Classification Model.
Trains a calibrated TF-IDF + Ensemble Voting Classifier (Logistic Regression, Complement Naive Bayes, Calibrated SGD)
and exports the model bundle to backend/app/models/saved/scam_classifier/.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import VotingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import Pipeline


def clean_text(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^\d+[\.\)]\s*", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def load_dataset(data_dir: Path) -> pd.DataFrame:
    nonscam_file = data_dir / "English_NonScam.txt"
    scam_file = data_dir / "English_Scam.txt"

    with open(nonscam_file, "r", encoding="utf-8", errors="replace") as f:
        nonscam_raw = [p.strip() for p in re.split(r"\n\s*\n", f.read()) if p.strip()]

    with open(scam_file, "r", encoding="utf-8", errors="replace") as f:
        scam_lines = f.read().split("\n")
        scam_raw = []
        cur = []
        for line in scam_lines:
            l = line.strip()
            if not l:
                if cur:
                    scam_raw.append(" ".join(cur))
                    cur = []
                continue
            if re.match(r"^\d+[\.\)]\s*", l):
                if cur:
                    scam_raw.append(" ".join(cur))
                    cur = []
                cur.append(l)
            else:
                cur.append(l)
        if cur:
            scam_raw.append(" ".join(cur))

    nonscam_cleaned = [clean_text(t) for t in nonscam_raw if len(clean_text(t)) > 10]
    scam_cleaned = [clean_text(t) for t in scam_raw if len(clean_text(t)) > 10]

    df_nonscam = pd.DataFrame({"text": nonscam_cleaned, "label": 0, "label_name": "GENUINE"})
    df_scam = pd.DataFrame({"text": scam_cleaned, "label": 1, "label_name": "SCAM"})

    df = pd.concat([df_nonscam, df_scam], ignore_index=True)
    df = df.drop_duplicates(subset=["text"]).reset_index(drop=True)
    return df


def train_and_save_model():
    base_dir = Path(__file__).resolve().parent.parent.parent
    data_dir = base_dir / "data"
    save_dir = base_dir / "app" / "models" / "saved" / "scam_classifier"
    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading datasets from {data_dir}...")
    df = load_dataset(data_dir)
    print(f"Total unique dataset samples: {len(df)} (Non-Scam: {(df['label']==0).sum()}, Scam: {(df['label']==1).sum()})")

    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=0.20, random_state=42, stratify=df["label"]
    )

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),
        max_features=5000,
        sublinear_tf=True,
        strip_accents="unicode",
        lowercase=True,
        stop_words="english",
    )

    clf_lr = LogisticRegression(C=2.0, max_iter=1000, solver="liblinear", random_state=42)
    clf_cnb = ComplementNB(alpha=0.5)
    clf_sgd = CalibratedClassifierCV(SGDClassifier(loss="hinge", max_iter=1000, random_state=42), cv=3)

    ensemble = VotingClassifier(
        estimators=[("lr", clf_lr), ("cnb", clf_cnb), ("sgd", clf_sgd)],
        voting="soft",
    )

    pipeline = Pipeline([("tfidf", vectorizer), ("clf", ensemble)])

    print("Running 5-fold cross validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="f1")
    print(f"Mean CV F1 Score: {cv_scores.mean():.4f} (±{cv_scores.std():.4f})")

    print("Fitting model on training set...")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)

    print("\n--- Test Set Evaluation ---")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print(f"ROC AUC:   {auc:.4f}")
    print(f"Confusion Matrix:\n{cm}")
    print("\nClassification Report:\n", classification_report(y_test, y_pred, target_names=["GENUINE", "SCAM"]))

    output_path = save_dir / "scam_classifier_pipeline.joblib"
    joblib.dump(
        {
            "pipeline": pipeline,
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1),
            "confusion_matrix": cm.tolist(),
            "classes": ["GENUINE", "SCAM"],
            "n_samples": len(df),
            "trained_at": pd.Timestamp.now().isoformat(),
        },
        str(output_path),
    )
    print(f"Model saved successfully to {output_path}")


if __name__ == "__main__":
    train_and_save_model()
