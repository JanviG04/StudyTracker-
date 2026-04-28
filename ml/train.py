"""Train the focus-risk classifier from sessions in the database.

Usage:
    python -m ml.train --user-id 1
    python -m ml.train --all-users
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# Allow running as `python ml/train.py` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db_config import get_connection  # noqa: E402
from ml.focus_classifier import save_model, train  # noqa: E402
from ml.sentiment import score_text  # noqa: E402


def fetch_sessions(user_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        if user_id is None:
            cursor.execute(
                """
                SELECT user_id, subject, hours, mood, session_date,
                       COALESCE(notes, '') AS notes,
                       sentiment_score, created_at
                FROM study_sessions
                ORDER BY user_id, session_date
                """
            )
        else:
            cursor.execute(
                """
                SELECT user_id, subject, hours, mood, session_date,
                       COALESCE(notes, '') AS notes,
                       sentiment_score, created_at
                FROM study_sessions
                WHERE user_id = %s
                ORDER BY session_date
                """,
                (user_id,),
            )
        return pd.DataFrame(cursor.fetchall())
    finally:
        cursor.close()
        connection.close()


def backfill_sentiment(df):
    """Compute sentiment for any rows that don't have it yet."""
    if df.empty:
        return df
    mask = df["sentiment_score"].isna()
    if mask.any():
        df.loc[mask, "sentiment_score"] = df.loc[mask, "notes"].apply(score_text)
    return df


def main():
    parser = argparse.ArgumentParser(description="Train focus-risk classifier")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--user-id", type=int, help="Train on a single user's sessions")
    group.add_argument("--all-users", action="store_true", help="Train on all users' sessions combined")
    args = parser.parse_args()

    print("Loading sessions from MySQL...")
    df = fetch_sessions(None if args.all_users else args.user_id)
    print(f"  loaded {len(df)} session rows")

    if df.empty:
        print("No sessions found. Log some study sessions in the app first.")
        return 1

    df = backfill_sentiment(df)

    print("Training logistic regression...")
    pipeline, metrics = train(df)
    print(f"  test accuracy: {metrics['accuracy']:.3f}")
    print(f"  train rows:    {metrics['n_train']}")
    print(f"  test rows:     {metrics['n_test']}")

    path = save_model(pipeline)
    print(f"Saved model to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
