"""Database connection helpers.

Local development uses SQLite. On Vercel, set `DATABASE_URL` to a Postgres connection
string (e.g. from Vercel Postgres) to use Postgres instead. The same application SQL
works on both backends thanks to `db_compat.CompatConnection`.
"""
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from flask import current_app, g

from db_compat import CompatConnection

ROOT = Path(__file__).resolve().parent.parent
POSTGRES_SCHEMA = "g9_venue_booking"


def _is_postgres():
    return bool(os.environ.get("DATABASE_URL"))


def database_path():
    path_str = os.environ.get("DATABASE_PATH", "data/venues.db")
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _postgres_connect(url):
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    psycopg2.extras.register_uuid()
    # Rùa Toán shares this Neon database with other projects. Keep all venue-booking
    # tables and enum types in a dedicated schema so app DDL cannot collide with theirs.
    with conn.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{POSTGRES_SCHEMA}"')
        cursor.execute(f'SET search_path TO "{POSTGRES_SCHEMA}", public')
    return CompatConnection(conn, "postgres")


def _sqlite_connect(path=None):
    conn = sqlite3.connect(path or database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return CompatConnection(conn, "sqlite")


def connect(path=None):
    """Open a database connection (Postgres if DATABASE_URL is set, otherwise SQLite)."""
    if _is_postgres():
        return _postgres_connect(os.environ["DATABASE_URL"])
    return _sqlite_connect(path)


def get_db():
    """The connection for the current request: opened on first use, closed by close_db()."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()
