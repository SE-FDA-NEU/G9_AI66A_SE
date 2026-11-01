"""Tests for Vercel/serverless deployment configuration.

These tests verify backend selection (SQLite vs Postgres) and storage selection
(local disk vs Cloudinary) without requiring real external services.
"""
import sys
import types
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class _MockFileStorage:
    """Minimal stand-in for a Werkzeug FileStorage."""

    def __init__(self, filename, content=b"fake image"):
        self.filename = filename
        self.stream = BytesIO(content)

    def save(self, destination):
        Path(destination).write_bytes(self.stream.read())


# ---------------------------------------------------------------------------
# Database backend selection
# ---------------------------------------------------------------------------

def test_sqlite_backend_selected_by_default(monkeypatch):
    """Without DATABASE_URL the app connects through the SQLite backend."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    import db

    conn = db.connect()
    assert conn._backend == "sqlite"
    conn.close()


def test_postgres_backend_selected_when_database_url_set(monkeypatch, tmp_path):
    """With DATABASE_URL the app connects through the Postgres backend."""
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@localhost/db")

    mock_pg = types.ModuleType("psycopg2")
    mock_extras = types.ModuleType("psycopg2.extras")
    mock_extras.register_uuid = lambda: None
    mock_extras.RealDictCursor = object
    mock_conn = MagicMock()
    mock_pg.connect = lambda url, cursor_factory=None: mock_conn
    mock_pg.extras = mock_extras
    sys.modules["psycopg2"] = mock_pg
    sys.modules["psycopg2.extras"] = mock_extras

    import db

    conn = db.connect()
    assert conn._backend == "postgres"
    assert conn._conn is mock_conn
    conn.close()

    del sys.modules["psycopg2"]
    del sys.modules["psycopg2.extras"]


def test_ensure_schema_creates_sqlite_file_idempotently(monkeypatch, tmp_path):
    """Schema creation is non-destructive and only runs when the DB file is absent."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db_path = tmp_path / "fresh.db"

    import app
    import db as db_module

    # First call creates the file and schema.
    app._ensure_schema(database=db_path)
    assert db_path.exists()

    mtime = db_path.stat().st_mtime

    # Second call leaves the existing file untouched.
    app._ensure_schema(database=db_path)
    assert db_path.stat().st_mtime == mtime


# ---------------------------------------------------------------------------
# Photo storage backend selection
# ---------------------------------------------------------------------------

def test_local_photo_storage_writes_to_disk(tmp_path, monkeypatch):
    """Without Cloudinary config, save_photo stores files locally under UPLOAD_DIR."""
    monkeypatch.delenv("CLOUDINARY_URL", raising=False)
    monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
    import storage

    photo = _MockFileStorage("pitch.jpg")
    file_name = storage.save_photo(tmp_path / "uploads", photo, venue_id=7)
    assert file_name.startswith("venue7-")
    assert file_name.endswith(".jpg")
    assert (tmp_path / "uploads" / file_name).exists()


def test_cloudinary_photo_storage_when_configured(monkeypatch):
    """With Cloudinary config, save_photo uploads to Cloudinary and returns a public_id."""
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://key:secret@cloud")

    mock_cloudinary = types.ModuleType("cloudinary")
    mock_uploader = types.ModuleType("cloudinary.uploader")
    uploaded = {"public_id": "sports-venue/venue7-abc123"}
    mock_uploader.upload = lambda photo, public_id: uploaded
    mock_cloudinary.config_from_url = lambda url: None
    mock_cloudinary.config = lambda **kwargs: None
    mock_cloudinary.uploader = mock_uploader
    mock_cloudinary.CloudinaryImage = MagicMock
    sys.modules["cloudinary"] = mock_cloudinary
    sys.modules["cloudinary.uploader"] = mock_uploader

    import storage

    photo = _MockFileStorage("pitch.jpg")
    file_name = storage.save_photo(Path("unused"), photo, venue_id=7)
    assert file_name == "sports-venue/venue7-abc123"

    del sys.modules["cloudinary"]
    del sys.modules["cloudinary.uploader"]


def test_postgres_sql_quotes_user_table():
    """The compat layer quotes the Postgres reserved word `user` when it is the table name."""
    import db_compat

    cursor = db_compat.CompatCursor(None, "postgres")
    sql, _ = cursor._translate("SELECT * FROM user WHERE id = ?", (1,))
    assert 'FROM "user"' in sql

    sql, _ = cursor._translate("INSERT INTO user (email) VALUES (?)", ("a",))
    assert 'INTO "user"' in sql

    sql, _ = cursor._translate("UPDATE user SET failed_login_count = ?", (0,))
    assert 'UPDATE "user"' in sql

    sql, _ = cursor._translate("JOIN user u ON u.id = b.customer_id", None)
    assert 'JOIN "user"' in sql


def test_photo_route_redirects_to_cloudinary_when_configured(monkeypatch, tmp_path):
    """The photo endpoint redirects to Cloudinary URLs when Cloudinary is configured."""
    monkeypatch.setenv("CLOUDINARY_URL", "cloudinary://key:secret@cloud")

    mock_cloudinary = types.ModuleType("cloudinary")
    mock_uploader = types.ModuleType("cloudinary.uploader")
    mock_cloudinary.config_from_url = lambda url: None
    mock_cloudinary.config = lambda **kwargs: None
    mock_image = MagicMock()
    mock_image.build_url.return_value = "https://res.cloudinary.com/demo/image/upload/v1/x"
    mock_cloudinary.CloudinaryImage = MagicMock(return_value=mock_image)
    mock_cloudinary.uploader = mock_uploader
    sys.modules["cloudinary"] = mock_cloudinary
    sys.modules["cloudinary.uploader"] = mock_uploader

    import db
    import app
    from init_db import seed

    db_path = tmp_path / "test.db"
    with db.connect(db_path) as conn:
        seed(conn)
        conn.execute(
            "INSERT INTO venue_photo (venue_id, file_name) VALUES (?, ?)",
            (1, "sports-venue/venue1-test"),
        )

    application = app.create_app(database=db_path)
    with application.test_client() as client:
        response = client.get("/venues/1/photos/1", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["Location"] == "https://res.cloudinary.com/demo/image/upload/v1/x"

    del sys.modules["cloudinary"]
    del sys.modules["cloudinary.uploader"]


def test_compat_row_indexing_and_normalization():
    """CompatRow supports indexing by int (row[0]), slice, key, and normalizes datetimes."""
    from datetime import datetime, date
    import db_compat

    now_dt = datetime(2026, 11, 1, 14, 0, 0)
    now_date = date(2026, 11, 1)
    raw = {"count": 42, "created_at": now_dt, "day": now_date, "name": "San Ho"}
    row = db_compat.CompatRow(raw)

    assert row[0] == 42
    assert row[1] == "2026-11-01 14:00"
    assert row[2] == "2026-11-01"
    assert row[3] == "San Ho"
    assert row[:2] == [42, "2026-11-01 14:00"]
    assert row["count"] == 42
    assert row.get("created_at") == "2026-11-01 14:00"
    assert dict(row)["count"] == 42


def test_postgres_sql_translation_preserves_typecasts():
    """Named parameters must not corrupt PostgreSQL ::typecasts."""
    import db_compat

    cursor = db_compat.CompatCursor(None, "postgres")
    sql, _ = cursor._translate(
        "SELECT date(slot_start) FROM booking WHERE :sport = sport AND date(slot_start) = :day",
        {"sport": "Football", "day": "2026-11-01"},
    )
    assert "slot_start::date" in sql
    assert "%(sport)s" in sql
    assert "%(day)s" in sql
    assert "::%(date)s" not in sql


def test_postgres_executescript():
    """CompatConnection.executescript executes multi-statement DDL on Postgres cursor."""
    import db_compat

    mock_raw_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_raw_conn.cursor.return_value.__enter__.return_value = mock_cursor

    conn = db_compat.CompatConnection(mock_raw_conn, "postgres")
    conn.executescript("CREATE TABLE test (id int);")
    mock_cursor.execute.assert_called_once_with("CREATE TABLE test (id int);")

