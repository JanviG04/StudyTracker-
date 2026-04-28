"""MySQL connection config for Smart Study Tracker.

Credentials are read from environment variables. Copy `.env.example` to `.env`
and fill in the values, or export them in your shell before running the app.
"""

import os

import mysql.connector

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


_DEFAULTS = {
    "host": "127.0.0.1",
    "port": "3306",
    "user": "root",
    "database": "study_tracker",
}


def get_db_settings():
    password = os.getenv("STUDY_TRACKER_DB_PASSWORD")
    if password is None:
        raise RuntimeError(
            "STUDY_TRACKER_DB_PASSWORD is not set. "
            "Copy .env.example to .env and fill in your MySQL credentials, "
            "or export the STUDY_TRACKER_DB_* environment variables."
        )

    return {
        "host": os.getenv("STUDY_TRACKER_DB_HOST", _DEFAULTS["host"]),
        "port": int(os.getenv("STUDY_TRACKER_DB_PORT", _DEFAULTS["port"])),
        "user": os.getenv("STUDY_TRACKER_DB_USER", _DEFAULTS["user"]),
        "password": password,
        "database": os.getenv("STUDY_TRACKER_DB_NAME", _DEFAULTS["database"]),
    }


def get_server_connection():
    settings = get_db_settings()
    return mysql.connector.connect(
        host=settings["host"],
        port=settings["port"],
        user=settings["user"],
        password=settings["password"],
    )


def get_connection():
    return mysql.connector.connect(**get_db_settings())
