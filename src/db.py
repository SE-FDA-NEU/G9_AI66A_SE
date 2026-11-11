"""Database connection helpers.

Local development uses SQLite. On Vercel, set `DATABASE_URL` to a Postgres connection
string (e.g. from Vercel Postgres) to use Postgres instead. The same application SQL
works on both backends thanks to `db_compat.CompatConnection`.
"""
import os
import sqlite3
import threading
from pathlib import Path
from urllib.parse import urlparse

from flask import current_app, g

from db_compat import CompatConnection

ROOT = Path(__file__).resolve().parent.parent
POSTGRES_SCHEMA = "g9_venue_booking"

_THREAD_LOCAL = threading.local()


def _is_postgres():
    return bool(os.environ.get("DATABASE_URL"))


def database_path():
    path_str = os.environ.get("DATABASE_PATH", "data/venues.db")
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _postgres_connect(url):
    import psycopg2
    import psycopg2.extras

    kwargs = {
        "cursor_factory": psycopg2.extras.RealDictCursor,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 3,
    }
    try:
        conn = psycopg2.connect(
            url,
            options=f"-c search_path={POSTGRES_SCHEMA},public",
            **kwargs,
        )
    except TypeError:
        # Fallback for unit tests where connect() mock lacks options or keepalive arguments
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)

    psycopg2.extras.register_uuid()
    return CompatConnection(conn, "postgres")


def _is_connection_alive(conn):
    """Verify underlying socket is active without relying solely on client-side status."""
    try:
        if conn._conn.closed:
            return False
        with conn._conn.cursor() as cur:
            cur.execute("SELECT 1")
        return True
    except Exception:
        return False


def _get_reusable_postgres_conn():
    conn = getattr(_THREAD_LOCAL, "pg_conn", None)
    if conn is not None:
        if _is_connection_alive(conn):
            try:
                conn._conn.rollback()  # Ensure clean STATUS_READY state
                return conn
            except Exception:
                pass
        # Connection dead or timed out by Neon; safely clean up
        try:
            conn.close()
        except Exception:
            pass
        _THREAD_LOCAL.pg_conn = None

    new_conn = _postgres_connect(os.environ["DATABASE_URL"])
    _THREAD_LOCAL.pg_conn = new_conn
    return new_conn


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
        if _is_postgres():
            g.db = _get_reusable_postgres_conn()
        else:
            g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        if _is_postgres():
            try:
                # Never auto-commit here; business transactions commit explicitly.
                # Rollback ensures clean state and releases uncommitted locks.
                conn.rollback()
            except Exception:
                try:
                    conn.close()
                except Exception:
                    pass
                _THREAD_LOCAL.pg_conn = None
        else:
            conn.close()

