"""Focus-risk classifier.

Predicts whether an upcoming study session is at risk of being "low-focus"
based on engineered features:
    - hours studied (planned)
    - mood (one-hot encoded)
    - hour-of-day
    - day-of-week
    - days since last session (recency)
    - rolling 7-day hours total
    - sentiment score of latest note (if available)

Label (training):
    Low-focus = mood in {"Stressed", "Tired"} OR sentiment <= -0.2
    High-focus = mood in {"Focused"} AND sentiment >= 0.0
    Other rows are dropped from training to give the model a cleaner signal.

Model: scikit-learn LogisticRegression inside a Pipeline with StandardScaler
on numeric features and one-hot encoding on mood. Persisted via joblib.
"""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import joblib


MOOD_VALUES = ["Focused", "Happy", "Tired", "Stressed"]
NUMERIC_FEATURES = [
    "hours",
    "hour_of_day",
    "day_of_week",
    "days_since_last",
    "rolling_7d_hours",
    "sentiment_score",
]
CATEGORICAL_FEATURES = ["mood"]
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "focus_classifier.joblib"


def build_features(sessions_df):
    """Take a raw sessions dataframe and return engineered features + labels.

    Expected columns: session_date, hours, mood, notes, sentiment_score,
    created_at (optional). All sessions for a single user.
    """
    df = sessions_df.copy()
    df["session_date"] = pd.to_datetime(df["session_date"])
    df = df.sort_values("session_date").reset_index(drop=True)

    df["hour_of_day"] = pd.to_datetime(df.get("created_at", df["session_date"])).dt.hour.fillna(12)
    df["day_of_week"] = df["session_date"].dt.dayofweek

    df["days_since_last"] = df["session_date"].diff().dt.days.fillna(0).clip(lower=0, upper=14)

    df["rolling_7d_hours"] = (
        df.set_index("session_date")["hours"]
        .rolling("7D")
        .sum()
        .reset_index(drop=True)
    )

    df["sentiment_score"] = df.get("sentiment_score", 0.0).fillna(0.0)

    df["mood"] = df["mood"].where(df["mood"].isin(MOOD_VALUES), other="Focused")

    return df


def _label_row(row):
    if row["mood"] in {"Stressed", "Tired"} or row["sentiment_score"] <= -0.2:
        return 1  # low-focus
    if row["mood"] == "Focused" and row["sentiment_score"] >= 0.0:
        return 0  # high-focus
    return np.nan


def train(sessions_df, test_size=0.25, random_state=42):
    """Train and return (pipeline, metrics_dict). Caller decides whether to save."""
    df = build_features(sessions_df)
    df["label"] = df.apply(_label_row, axis=1)
    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)

    if len(df) < 12 or df["label"].nunique() < 2:
        raise ValueError(
            f"Not enough labeled rows to train (have {len(df)}, "
            f"classes={df['label'].nunique()}). Log more sessions and retry."
        )

    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    X = df[feature_cols]
    y = df["label"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(categories=[MOOD_VALUES], handle_unknown="ignore"),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "report": classification_report(y_test, y_pred, output_dict=True, zero_division=0),
    }
    return pipeline, metrics


def save_model(pipeline, path=MODEL_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, path)
    return path


def load_model(path=MODEL_PATH):
    path = Path(path)
    if not path.exists():
        return None
    return joblib.load(path)


def predict_focus_risk(features, pipeline=None):
    """Return P(low-focus) in [0, 1]. Returns None if no model is loaded.

    `features` is a dict with keys matching NUMERIC_FEATURES + CATEGORICAL_FEATURES.
    """
    pipeline = pipeline or load_model()
    if pipeline is None:
        return None

    row = pd.DataFrame([{key: features.get(key) for key in NUMERIC_FEATURES + CATEGORICAL_FEATURES}])
    for col in NUMERIC_FEATURES:
        row[col] = pd.to_numeric(row[col], errors="coerce").fillna(0.0)
    if row["mood"].iloc[0] not in MOOD_VALUES:
        row["mood"] = "Focused"

    proba = pipeline.predict_proba(row)[0]
    classes = list(pipeline.classes_)
    if 1 in classes:
        return float(proba[classes.index(1)])
    return 0.0


def context_features_from_sessions(sessions_df, planned_hours, planned_mood):
    """Build a feature dict for predicting an UPCOMING session,
    using the user's recent history as context.
    """
    today = pd.Timestamp(date.today())

    if sessions_df is None or len(sessions_df) == 0:
        return {
            "hours": float(planned_hours),
            "hour_of_day": today.hour,
            "day_of_week": today.dayofweek,
            "days_since_last": 14.0,
            "rolling_7d_hours": 0.0,
            "sentiment_score": 0.0,
            "mood": planned_mood if planned_mood in MOOD_VALUES else "Focused",
        }

    df = build_features(sessions_df)
    last = df.iloc[-1]
    days_since_last = max(0, (today - pd.to_datetime(last["session_date"])).days)
    seven_day_window = df[df["session_date"] >= today - pd.Timedelta(days=7)]
    rolling_7d = float(seven_day_window["hours"].sum())

    return {
        "hours": float(planned_hours),
        "hour_of_day": today.hour,
        "day_of_week": today.dayofweek,
        "days_since_last": float(days_since_last),
        "rolling_7d_hours": rolling_7d,
        "sentiment_score": float(last.get("sentiment_score") or 0.0),
        "mood": planned_mood if planned_mood in MOOD_VALUES else "Focused",
    }
