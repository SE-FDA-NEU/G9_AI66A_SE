"""Database compatibility layer: run the same application SQL on SQLite and Postgres.

The application uses sqlite3 parameter styles (`?` positional and `:name` named) and a
few SQLite-only expressions. When `DATABASE_URL` is present the app connects to Postgres;
this module translates the SQL and result shapes so the rest of the codebase does not
need to change.
"""
import re


class CompatRow:
    """Dict-like and tuple-like row that works for both sqlite3.Row and psycopg2 RealDictRow."""

    def __init__(self, data):
        self._data = data

    @staticmethod
    def _normalize(val):
        from datetime import date, datetime
        if isinstance(val, datetime):
            return val.strftime("%Y-%m-%d %H:%M:%S") if val.second else val.strftime("%Y-%m-%d %H:%M")
        if isinstance(val, date):
            return val.isoformat()
        return val

    def __getitem__(self, key):
        if isinstance(key, slice):
            return [self._normalize(v) for v in list(self._data.values())[key]]
        if isinstance(key, int):
            val = list(self._data.values())[key]
        else:
            val = self._data[key]
        return self._normalize(val)

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return key in self._data

    def keys(self):
        return self._data.keys()

    def values(self):
        return [self._normalize(v) for v in self._data.values()]

    def items(self):
        return [(k, self._normalize(v)) for k, v in self._data.items()]

    def get(self, key, default=None):
        if key in self._data:
            return self._normalize(self._data[key])
        return default


class CompatCursor:
    """Cursor-like wrapper that normalises placeholders, functions and lastrowid."""

    def __init__(self, raw_cursor, backend):
        self._cursor = raw_cursor
        self._backend = backend
        self.lastrowid = None
        self.rowcount = 0

    def _translate(self, sql, params):
        if self._backend == "sqlite":
            return sql, params

        # Postgres path
        translated = sql

        # Convert SQLite BEGIN IMMEDIATE to standard BEGIN
        if re.match(r"^\s*BEGIN\s+IMMEDIATE", translated, re.IGNORECASE):
            translated = re.sub(r"^\s*BEGIN\s+IMMEDIATE", "BEGIN", translated, flags=re.IGNORECASE)

        # Convert date(col) -> col::date (including table.column or alias.column)
        translated = re.sub(r"\bdate\(\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\)", r"\1::date", translated)

        # Convert datetime('now') -> NOW()
        translated = re.sub(r"datetime\(\s*'now'\s*\)", "NOW()", translated, flags=re.IGNORECASE)

        # Handle Postgres timestamp parameter typecast in COALESCE
        translated = re.sub(
            r"COALESCE\s*\(\s*email_verified_at\s*,\s*\?\s*\)",
            "COALESCE(email_verified_at, (?)::timestamp)",
            translated,
            flags=re.IGNORECASE,
        )

        # Convert strftime('%w', col) -> EXTRACT(DOW FROM col)::int
        translated = re.sub(
            r"strftime\(\s*'%w'\s*,\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)",
            r"EXTRACT(DOW FROM \1)::int",
            translated,
        )

        # Quote the reserved word `user` when it refers to the user table. This is safe
        # because SQLite also accepts double-quoted identifiers.
        translated = re.sub(
            r"\b(FROM|JOIN|INTO|UPDATE|TABLE|REFERENCES)\s+user\b",
            r'\1 "user"',
            translated,
            flags=re.IGNORECASE,
        )

        # Convert ? placeholders to %s
        if "?" in translated and params is not None and not isinstance(params, dict):
            translated = translated.replace("?", "%s")

        # Convert :name placeholders to %(name)s (with negative lookbehind so ::typecasts are preserved)
        if isinstance(params, dict):
            translated = re.sub(r"(?<!:):([a-zA-Z_][a-zA-Z0-9_]*)", r"%(\1)s", translated)

        # INSERT OR REPLACE -> INSERT ... ON CONFLICT DO UPDATE for blocked_slot only.
        # This is the only OR REPLACE used by the application.
        if re.search(r"INSERT\s+OR\s+REPLACE", translated, re.IGNORECASE):
            translated = re.sub(
                r"INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s+\(([^)]+)\)\s+VALUES\s+\(([^)]+)\)",
                r"INSERT INTO \1 (\2) VALUES (\3) ON CONFLICT (venue_id, slot_start) DO UPDATE SET reason = EXCLUDED.reason",
                translated,
                flags=re.IGNORECASE,
            )

        return translated, params

    def _add_returning_id(self, sql):
        """Append RETURNING id to INSERT statements that do not already return rows."""
        if not re.match(r"\s*INSERT\s+INTO", sql, re.IGNORECASE):
            return sql
        if re.search(r"RETURNING\s+", sql, re.IGNORECASE):
            return sql
        return sql.rstrip().rstrip(";") + " RETURNING id"

    def execute(self, sql, params=None):
        translated, params = self._translate(sql, params)

        if self._backend == "postgres":
            translated = self._add_returning_id(translated)

        self._cursor.execute(translated, params if params is not None else ())
        self.rowcount = self._cursor.rowcount

        if re.match(r"\s*INSERT", translated, re.IGNORECASE):
            if self._backend == "postgres":
                row = self._cursor.fetchone() if self._cursor.description is not None else None
                self.lastrowid = row["id"] if isinstance(row, dict) else row[0] if row else None
            else:
                self.lastrowid = self._cursor.lastrowid

        return self

    def _wrap_row(self, row):
        if row is None:
            return None
        if isinstance(row, dict):
            return CompatRow(row)
        return row

    def fetchone(self):
        return self._wrap_row(self._cursor.fetchone())

    def fetchall(self):
        rows = self._cursor.fetchall()
        if rows and isinstance(rows[0], dict):
            return [CompatRow(r) for r in rows]
        return rows

    def __iter__(self):
        for row in self._cursor:
            yield self._wrap_row(row)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class CompatConnection:
    """Connection wrapper exposing execute/commit/close/executescript used by the app."""

    def __init__(self, raw_conn, backend):
        self._conn = raw_conn
        self._backend = backend

    def cursor(self):
        return CompatCursor(self._conn.cursor(), self._backend)

    def execute(self, sql, params=None):
        cur = self.cursor()
        return cur.execute(sql, params)

    def executescript(self, sql):
        """Run a script containing multiple statements."""
        if self._backend == "sqlite":
            self._conn.executescript(sql)
            return self

        # Postgres: run the whole DDL script in one go. The Postgres schema only contains
        # idempotent CREATE IF NOT EXISTS statements, so repeated runs are safe.
        with self._conn.cursor() as cur:
            cur.execute(sql)
        return self

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._conn.close()
        return False

    @property
    def in_transaction(self):
        if self._backend == "postgres":
            try:
                import psycopg2.extensions
                return self._conn.status == psycopg2.extensions.STATUS_IN_TRANSACTION
            except Exception:
                return False
        return getattr(self._conn, "in_transaction", False)

    def __getattr__(self, name):
        return getattr(self._conn, name)
