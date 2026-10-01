"""Database connection helpers. Every module opens SQLite through here."""
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def database_path():
    return ROOT / os.environ.get("DATABASE_PATH", "data/venues.db")


def connect(path=None):
    conn = sqlite3.connect(path or database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
