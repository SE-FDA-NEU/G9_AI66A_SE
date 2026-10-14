"""Database connection helpers. Every module opens SQLite through here."""
import os
import sqlite3
from pathlib import Path

from flask import current_app, g

ROOT = Path(__file__).resolve().parent.parent


def database_path():
    return ROOT / os.environ.get("DATABASE_PATH", "data/venues.db")


def connect(path=None):
    conn = sqlite3.connect(path or database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """The connection for the current request: opened on first use, closed by close_db()."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()
