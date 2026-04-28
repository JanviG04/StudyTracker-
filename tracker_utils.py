import hashlib
import hmac
import os
from datetime import date, datetime

import mysql.connector

from db_config import get_connection, get_db_settings, get_server_connection
from ml.sentiment import label_from_score, score_text


def _hash_password(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{digest.hex()}"


def _verify_password(password, stored_value):
    if ":" not in stored_value:
        return hmac.compare_digest(stored_value, password)

    salt_hex, digest_hex = stored_value.split(":", 1)
    expected = _hash_password(password, bytes.fromhex(salt_hex)).split(":", 1)[1]
    return hmac.compare_digest(expected, digest_hex)


def initialize_database():
    settings = get_db_settings()

    server_connection = get_server_connection()
    server_cursor = server_connection.cursor()
    try:
        server_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings['database']}")
        server_connection.commit()
    finally:
        server_cursor.close()
        server_connection.close()

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                subject VARCHAR(50) NOT NULL,
                hours DECIMAL(5, 2) NOT NULL,
                mood VARCHAR(30) NOT NULL,
                session_date DATE NOT NULL,
                notes VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS login_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                username VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL,
                login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INT PRIMARY KEY,
                daily_goal_hours DECIMAL(4, 2) NOT NULL DEFAULT 2.00,
                last_streak_popup_date DATE NULL,
                last_goal_popup_date DATE NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_badges (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                badge_code VARCHAR(50) NOT NULL,
                badge_name VARCHAR(100) NOT NULL,
                awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_badge (user_id, badge_code),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        _add_column_if_missing(cursor, "users", "created_at", "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        _add_column_if_missing(cursor, "study_sessions", "notes", "notes VARCHAR(255)")
        _add_column_if_missing(cursor, "study_sessions", "sentiment_score", "sentiment_score FLOAT NULL")
        _add_column_if_missing(cursor, "study_sessions", "predicted_focus", "predicted_focus FLOAT NULL")
        _add_column_if_missing(
            cursor,
            "study_sessions",
            "created_at",
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        )
        _add_column_if_missing(cursor, "login_history", "login_at", "login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        _add_column_if_missing(cursor, "user_preferences", "last_streak_popup_date", "last_streak_popup_date DATE NULL")
        _add_column_if_missing(cursor, "user_preferences", "last_goal_popup_date", "last_goal_popup_date DATE NULL")
        _add_column_if_missing(
            cursor,
            "user_preferences",
            "updated_at",
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def _add_column_if_missing(cursor, table_name, column_name, definition):
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = %s
          AND column_name = %s
        """,
        (table_name, column_name),
    )
    if cursor.fetchone()[0]:
        return
    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {definition}")


def register_user(username, password):
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, _hash_password(password)),
        )
        connection.commit()
        return True, "Registered successfully."
    except mysql.connector.IntegrityError:
        return False, "Username already exists."
    finally:
        cursor.close()
        connection.close()


def login_user(username, password):
    username = username.strip()
    if not username or not password:
        _record_login_event(username, None, "failed")
        return None

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, username, password FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if not user or not _verify_password(password, user["password"]):
            _record_login_event(username, None, "failed")
            return None
        _record_login_event(user["username"], user["id"], "success")
        return {"id": user["id"], "username": user["username"]}
    finally:
        cursor.close()
        connection.close()


def log_study_session(user_id, subject, hours, mood, session_date_text=None, notes=""):
    if not user_id:
        raise ValueError("You must log in before saving a study session.")

    subject = subject.strip()
    mood = mood.strip()
    notes = notes.strip()

    if not subject:
        raise ValueError("Subject is required.")
    if hours <= 0:
        raise ValueError("Hours studied must be greater than zero.")
    if not mood:
        raise ValueError("Mood is required.")

    session_date = _parse_session_date(session_date_text)
    sentiment_score = score_text(notes)

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO study_sessions
                (user_id, subject, hours, mood, session_date, notes, sentiment_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (user_id, subject, hours, mood, session_date, notes or None, sentiment_score),
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def get_dashboard_summary(user_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN session_date = CURDATE() THEN hours ELSE 0 END), 0) AS today_hours,
                COALESCE(SUM(hours), 0) AS total_hours,
                COALESCE(SUM(CASE WHEN session_date >= CURDATE() - INTERVAL 6 DAY THEN hours ELSE 0 END), 0) AS weekly_hours,
                COUNT(*) AS total_sessions,
                MAX(session_date) AS last_session_date
            FROM study_sessions
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        return {
            "today_hours": float(row["today_hours"] or 0),
            "total_hours": float(row["total_hours"] or 0),
            "weekly_hours": float(row["weekly_hours"] or 0),
            "total_sessions": int(row["total_sessions"] or 0),
            "last_session_date": row["last_session_date"],
        }
    finally:
        cursor.close()
        connection.close()


def get_subject_breakdown(user_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT subject, ROUND(SUM(hours), 2) AS total_hours
            FROM study_sessions
            WHERE user_id = %s
            GROUP BY subject
            ORDER BY total_hours DESC, subject ASC
            """,
            (user_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def get_recent_sessions(user_id, limit=10):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT subject, hours, mood, session_date,
                   COALESCE(notes, '') AS notes,
                   sentiment_score
            FROM study_sessions
            WHERE user_id = %s
            ORDER BY session_date DESC, id DESC
            LIMIT %s
            """,
            (user_id, limit),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def get_daily_progress(user_id, days=7):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            WITH RECURSIVE day_range AS (
                SELECT CURDATE() - INTERVAL %s DAY AS day_value
                UNION ALL
                SELECT day_value + INTERVAL 1 DAY
                FROM day_range
                WHERE day_value < CURDATE()
            )
            SELECT
                day_range.day_value AS session_date,
                COALESCE(SUM(study_sessions.hours), 0) AS total_hours
            FROM day_range
            LEFT JOIN study_sessions
                ON study_sessions.user_id = %s
               AND study_sessions.session_date = day_range.day_value
            GROUP BY day_range.day_value
            ORDER BY day_range.day_value
            """,
            (max(days - 1, 0), user_id),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def get_user_preferences(user_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT user_id, daily_goal_hours, last_streak_popup_date, last_goal_popup_date
            FROM user_preferences
            WHERE user_id = %s
            """,
            (user_id,),
        )
        preferences = cursor.fetchone()
        if preferences:
            return {
                "user_id": preferences["user_id"],
                "daily_goal_hours": float(preferences["daily_goal_hours"]),
                "last_streak_popup_date": preferences["last_streak_popup_date"],
                "last_goal_popup_date": preferences["last_goal_popup_date"],
            }

        cursor.close()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO user_preferences (user_id, daily_goal_hours, last_streak_popup_date, last_goal_popup_date)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, 2.0, None, None),
        )
        connection.commit()
        return {
            "user_id": user_id,
            "daily_goal_hours": 2.0,
            "last_streak_popup_date": None,
            "last_goal_popup_date": None,
        }
    finally:
        cursor.close()
        connection.close()


def update_daily_goal(user_id, daily_goal_hours):
    if daily_goal_hours <= 0:
        raise ValueError("Daily goal must be greater than zero.")
    if daily_goal_hours > 16:
        raise ValueError("Daily goal should be realistic. Keep it at 16 hours or less.")

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO user_preferences (user_id, daily_goal_hours)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE daily_goal_hours = VALUES(daily_goal_hours)
            """,
            (user_id, daily_goal_hours),
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def get_study_streak(user_id):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT DISTINCT session_date
            FROM study_sessions
            WHERE user_id = %s
            ORDER BY session_date DESC
            """,
            (user_id,),
        )
        dates = [row[0] for row in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()

    if not dates:
        return 0

    streak = 0
    expected = date.today()
    if dates[0] < expected:
        expected = dates[0]

    date_set = set(dates)
    while expected in date_set:
        streak += 1
        expected = expected.fromordinal(expected.toordinal() - 1)
    return streak


def get_wellness_insights(user_id):
    recent_sessions = get_recent_sessions(user_id, limit=12)
    summary = get_dashboard_summary(user_id)
    preferences = get_user_preferences(user_id)
    streak_days = get_study_streak(user_id)
    return build_wellness_insights(recent_sessions, summary, preferences, streak_days)


def build_wellness_insights(recent_sessions, summary, preferences, streak_days):
    goal_hours = float(preferences["daily_goal_hours"])

    if not recent_sessions:
        return {
            "focus_score": 50,
            "headline": "Start small, stay consistent.",
            "message": "Log your first session today. Momentum matters more than intensity.",
            "action": "Try one 25-minute focus sprint and write one short note.",
            "streak_days": 0,
            "goal_hours": goal_hours,
            "avg_sentiment": 0.0,
            "sentiment_label": "neutral",
        }

    stressed_or_tired = sum(1 for row in recent_sessions if row["mood"] in {"Stressed", "Tired"})
    focused_sessions = sum(1 for row in recent_sessions if row["mood"] == "Focused")
    notes_blob = " ".join(row["notes"].lower() for row in recent_sessions if row["notes"])
    distraction_keywords = ("instagram", "reels", "youtube", "scroll", "phone", "game", "discord")
    distraction_hits = sum(1 for keyword in distraction_keywords if keyword in notes_blob)

    sentiment_values = [
        float(row["sentiment_score"])
        for row in recent_sessions
        if row.get("sentiment_score") is not None
    ]
    if sentiment_values:
        avg_sentiment = sum(sentiment_values) / len(sentiment_values)
    else:
        avg_sentiment = 0.0
    sentiment_label = label_from_score(avg_sentiment)
    negative_share = (
        sum(1 for value in sentiment_values if value <= -0.05) / max(len(sentiment_values), 1)
    )

    focus_score = 70
    focus_score += min(focused_sessions * 4, 16)
    focus_score -= stressed_or_tired * 5
    focus_score -= distraction_hits * 4
    focus_score += int(round(avg_sentiment * 12))
    if summary["today_hours"] >= goal_hours:
        focus_score += 8
    if streak_days >= 3:
        focus_score += 6
    focus_score = max(15, min(100, focus_score))

    headline = "Steady progress."
    message = "You are building consistency. Keep protecting your focus windows."
    action = "Repeat the same study start time tomorrow."

    if negative_share >= 0.5 and len(sentiment_values) >= 4:
        headline = "Your notes are trending negative."
        message = (
            f"Sentiment analysis flagged {negative_share:.0%} of recent notes as negative "
            "(VADER compound score)."
        )
        action = "Pause and journal one win before the next session — frame the positive first."
    elif distraction_hits >= 2:
        headline = "Distraction risk is rising."
        message = "Your recent notes suggest phone or scrolling interruptions are affecting deep work."
        action = "Use one 25-minute focus sprint with your phone out of reach."
    elif stressed_or_tired >= 4:
        headline = "Burnout warning."
        message = "A high number of tired or stressed sessions suggests your routine needs recovery time."
        action = "Take a short break, reduce task-switching, and aim for one simple win today."
    elif summary["today_hours"] < goal_hours * 0.5 and streak_days <= 1:
        headline = "Consistency needs support."
        message = "You are below your daily target and the streak is still fragile."
        action = "Lower the goal slightly and commit to a non-zero study session every day."
    elif focused_sessions >= 4 and avg_sentiment >= 0.1:
        headline = "Focus mode is working."
        message = "Recent sessions show a healthy pattern of focused work and positive notes."
        action = "Stretch one session by 10 extra minutes instead of starting a new task."

    return {
        "focus_score": focus_score,
        "headline": headline,
        "message": message,
        "action": action,
        "streak_days": streak_days,
        "goal_hours": goal_hours,
        "avg_sentiment": round(avg_sentiment, 3),
        "sentiment_label": sentiment_label,
    }


def get_focus_prediction(user_id, planned_hours, planned_mood):
    """Return P(low-focus) for an upcoming session, or None if no model is trained yet.

    Lazy-imports the ML modules so the desktop app doesn't pay sklearn/pandas
    import cost unless the model is actually present.
    """
    from pathlib import Path

    model_path = Path(__file__).resolve().parent / "models" / "focus_classifier.joblib"
    if not model_path.exists():
        return None

    import pandas as pd

    from ml.focus_classifier import (
        context_features_from_sessions,
        load_model,
        predict_focus_risk,
    )

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT subject, hours, mood, session_date,
                   COALESCE(notes, '') AS notes,
                   sentiment_score, created_at
            FROM study_sessions
            WHERE user_id = %s
            ORDER BY session_date
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()

    df = pd.DataFrame(rows)
    features = context_features_from_sessions(df, planned_hours, planned_mood)
    pipeline = load_model(model_path)
    return predict_focus_risk(features, pipeline=pipeline)


def get_user_badges(user_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT badge_code, badge_name, awarded_at
            FROM user_badges
            WHERE user_id = %s
            ORDER BY awarded_at DESC
            """,
            (user_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def mark_streak_popup_shown(user_id, popup_date):
    preferences = get_user_preferences(user_id)
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO user_preferences (user_id, daily_goal_hours, last_streak_popup_date, last_goal_popup_date)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE last_streak_popup_date = VALUES(last_streak_popup_date)
            """,
            (user_id, preferences["daily_goal_hours"], popup_date, preferences["last_goal_popup_date"]),
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def get_streak_status(user_id):
    preferences = get_user_preferences(user_id)
    summary = get_dashboard_summary(user_id)
    streak_days = get_study_streak(user_id)
    latest_streak_date = summary["last_session_date"]
    should_popup = bool(
        streak_days > 0
        and latest_streak_date
        and preferences["last_streak_popup_date"] != latest_streak_date
    )
    new_badges = _award_streak_badges(user_id, streak_days)
    badges = get_user_badges(user_id)
    return {
        "streak_days": streak_days,
        "latest_streak_date": latest_streak_date,
        "should_popup": should_popup,
        "new_badges": new_badges,
        "badges": badges,
    }


def mark_goal_popup_shown(user_id, popup_date):
    preferences = get_user_preferences(user_id)
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO user_preferences (user_id, daily_goal_hours, last_streak_popup_date, last_goal_popup_date)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE last_goal_popup_date = VALUES(last_goal_popup_date)
            """,
            (user_id, preferences["daily_goal_hours"], preferences["last_streak_popup_date"], popup_date),
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def get_goal_status(user_id):
    preferences = get_user_preferences(user_id)
    summary = get_dashboard_summary(user_id)
    today = date.today()
    goal_hours = preferences["daily_goal_hours"]
    reached = summary["today_hours"] >= goal_hours
    should_popup = reached and preferences["last_goal_popup_date"] != today
    return {
        "goal_hours": goal_hours,
        "today_hours": summary["today_hours"],
        "reached": reached,
        "should_popup": should_popup,
        "popup_date": today,
    }


def _award_streak_badges(user_id, streak_days):
    badge_rules = [
        (7, "streak_7", "7-Day Flame"),
        (14, "streak_14", "14-Day Momentum"),
        (30, "streak_30", "30-Day Legend"),
    ]
    awarded = []

    connection = get_connection()
    cursor = connection.cursor()
    try:
        for threshold, code, name in badge_rules:
            if streak_days < threshold:
                continue
            try:
                cursor.execute(
                    """
                    INSERT INTO user_badges (user_id, badge_code, badge_name)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, code, name),
                )
                awarded.append({"badge_code": code, "badge_name": name})
            except mysql.connector.IntegrityError:
                continue
        connection.commit()
    finally:
        cursor.close()
        connection.close()

    return awarded


def _parse_session_date(session_date_text):
    if not session_date_text or not session_date_text.strip():
        return date.today()

    try:
        return datetime.strptime(session_date_text.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Date must be in YYYY-MM-DD format.") from exc


def _record_login_event(username, user_id, status):
    safe_username = (username or "").strip() or "unknown"
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO login_history (user_id, username, status)
            VALUES (%s, %s, %s)
            """,
            (user_id, safe_username, status),
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()
