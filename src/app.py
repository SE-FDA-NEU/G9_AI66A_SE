"""Flask web app - Sports Venue Booking System.

Run from the repository root:  python src/app.py
Pages live in src/routes/ (one module per group of screens); business rules live in the
service modules (src/auth.py, ...). This file only wires them together.
"""
import importlib
import os
import pkgutil
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

import routes
from csrf import init_csrf
from db import ROOT, close_db, connect, get_db
from errors import BusinessRuleError
from guards import SESSION_TIMEOUT, load_user
from pg_schema import PG_SCHEMA
from ratelimit import init_ratelimit
from schema import SCHEMA
from time_utils import vn_now

load_dotenv()


def _migrate_postgres_columns(conn):
    """Idempotently add columns required by newer features to existing Postgres tables."""
    already_migrated = conn.execute(
        "SELECT 1 FROM information_schema.columns"
        " WHERE table_schema = current_schema() AND table_name = 'venue' AND column_name = 'latitude'"
        " LIMIT 1"
    ).fetchone()
    if already_migrated is not None:
        return
    statements = (
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS suspended INTEGER NOT NULL DEFAULT 0 CHECK (suspended IN (0, 1))',
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMP',
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS suspended_reason TEXT',
        'ALTER TABLE review ADD COLUMN IF NOT EXISTS report_count INTEGER NOT NULL DEFAULT 0 CHECK (report_count >= 0)',
        'ALTER TABLE review ADD COLUMN IF NOT EXISTS hidden INTEGER NOT NULL DEFAULT 0 CHECK (hidden IN (0, 1))',
        "ALTER TABLE review ADD COLUMN IF NOT EXISTS moderation_status TEXT NOT NULL DEFAULT 'active' CHECK (moderation_status IN ('active', 'pending', 'approved', 'rejected'))",
        'ALTER TABLE review ADD COLUMN IF NOT EXISTS moderated_at TIMESTAMP',
        'ALTER TABLE review ADD COLUMN IF NOT EXISTS moderated_by INTEGER REFERENCES "user"(id)',
        'ALTER TABLE venue ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION',
        'ALTER TABLE venue ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION',
    )
    for stmt in statements:
        conn.execute(stmt)
    conn.commit()


def _migrate_sqlite_columns(conn):
    """Idempotently add columns required by newer features to existing SQLite tables."""
    user_cols = {r[1] for r in conn.execute('PRAGMA table_info("user")').fetchall()}
    if user_cols:
        if "suspended" not in user_cols:
            conn.execute('ALTER TABLE "user" ADD COLUMN suspended INTEGER NOT NULL DEFAULT 0 CHECK (suspended IN (0, 1))')
        if "suspended_at" not in user_cols:
            conn.execute('ALTER TABLE "user" ADD COLUMN suspended_at TEXT')
        if "suspended_reason" not in user_cols:
            conn.execute('ALTER TABLE "user" ADD COLUMN suspended_reason TEXT')

    review_cols = {r[1] for r in conn.execute('PRAGMA table_info("review")').fetchall()}
    if review_cols:
        if "report_count" not in review_cols:
            conn.execute('ALTER TABLE review ADD COLUMN report_count INTEGER NOT NULL DEFAULT 0 CHECK (report_count >= 0)')
        if "hidden" not in review_cols:
            conn.execute('ALTER TABLE review ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0 CHECK (hidden IN (0, 1))')
        if "moderation_status" not in review_cols:
            conn.execute(
                "ALTER TABLE review ADD COLUMN moderation_status TEXT NOT NULL DEFAULT 'active'"
                " CHECK (moderation_status IN ('active', 'pending', 'approved', 'rejected'))"
            )
        if "moderated_at" not in review_cols:
            conn.execute('ALTER TABLE review ADD COLUMN moderated_at TEXT')
        if "moderated_by" not in review_cols:
            conn.execute('ALTER TABLE review ADD COLUMN moderated_by INTEGER REFERENCES user(id)')

    venue_cols = {r[1] for r in conn.execute('PRAGMA table_info("venue")').fetchall()}
    if venue_cols:
        if "latitude" not in venue_cols:
            conn.execute('ALTER TABLE venue ADD COLUMN latitude REAL')
        if "longitude" not in venue_cols:
            conn.execute('ALTER TABLE venue ADD COLUMN longitude REAL')

    conn.commit()


def _ensure_schema(database=None):
    """Create tables if they do not exist. Never drops or reseeds data."""
    if os.environ.get("DATABASE_URL"):
        with connect() as conn:
            try:
                conn.execute("SELECT 1 FROM venue LIMIT 1")
                _migrate_postgres_columns(conn)
                try:
                    has_popular = conn.execute(
                        "SELECT 1 FROM venue WHERE name = 'San Bong C500 (Hoc vien An Ninh)' LIMIT 1"
                    ).fetchone()
                    if has_popular is None:
                        from hanoi_popular_venues import sync_popular_venues
                        from pg_seed import sync_missing_venues_postgres
                        sync_missing_venues_postgres(conn)
                        sync_popular_venues(conn)
                except Exception as sync_exc:
                    import logging
                    logging.warning("Popular venue sync skipped: %s", sync_exc)
                return
            except Exception as exc:
                if getattr(exc, "pgcode", None) != "42P01" and "does not exist" not in str(exc).lower():
                    raise
                try:
                    conn.rollback()
                except Exception:
                    pass
            from db import POSTGRES_SCHEMA
            with conn._conn.cursor() as cur:
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{POSTGRES_SCHEMA}"')
            conn.executescript(PG_SCHEMA)
            from pg_seed import seed_postgres
            seed_postgres(conn)
        return
    # SQLite: only create the file/schema when it does not exist yet; migrate existing DBs.
    from db import database_path
    path = database_path() if database is None else Path(database)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with connect(path) as conn:
            conn.executescript(SCHEMA)
    else:
        with connect(path) as conn:
            _migrate_sqlite_columns(conn)


def wants_json():
    return request.path.startswith("/api/")


def create_app(database=None):
    app = Flask(__name__)
    if os.environ.get("PYTEST_CURRENT_TEST"):
        app.config["TESTING"] = True
    app.config.setdefault("NOW", vn_now)
    secret_key = os.environ.get("SECRET_KEY") or "dev-only"
    if (
        os.environ.get("DATABASE_URL")
        and not app.config.get("TESTING")
        and not app.debug
        and secret_key == "dev-only"
    ):
        raise RuntimeError("SECRET_KEY must be set in production when DATABASE_URL is configured")
    app.config["SECRET_KEY"] = secret_key
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["DATABASE"] = database
    app.config["PERMANENT_SESSION_LIFETIME"] = SESSION_TIMEOUT        # BR8
    app.config["UPLOAD_DIR"] = Path(os.environ.get("UPLOAD_DIR", ROOT / "data" / "uploads"))  # venue photos, git-ignored
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024                   # largest photo upload: 5 MB
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000

    _ensure_schema(database)

    init_csrf(app)
    init_ratelimit(app)

    app.before_request(load_user)
    app.teardown_appcontext(close_db)

    @app.after_request
    def apply_security_and_cache_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.path.startswith("/static/") or "/photos/" in request.path:
            return response
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
            response.headers["Pragma"] = "no-cache"
        return response

    for module in pkgutil.iter_modules(routes.__path__):
        app.register_blueprint(importlib.import_module(f"routes.{module.name}").bp)

    @app.errorhandler(BusinessRuleError)
    def business_rule_error(err):
        if wants_json():
            return jsonify(err.to_json()), err.status
        return render_template("error.html", message=err.message), err.status

    @app.errorhandler(404)
    def not_found(_err):
        message = "We could not find that page. Check the address, or start again from the search page."
        if wants_json():
            return jsonify(error="Not found"), 404
        return render_template("error.html", message=message), 404

    @app.errorhandler(413)
    def too_large(_err):
        message = "The photo is larger than 5 MB. Choose a smaller photo and add the venue again."
        if wants_json():
            return jsonify(error=message), 413
        return render_template("error.html", message=message), 413

    @app.errorhandler(500)
    def internal_error(_err):
        message = "Something went wrong on our end. Please try again later."
        if wants_json():
            return jsonify(error="Internal server error"), 500
        return render_template("error.html", message=message), 500

    @app.route("/health")
    def health():
        # Used by docs/SETUP.md and production uptime monitoring:
        # Returns 200 when app and database are healthy, 503 when not.
        try:
            venues = get_db().execute("SELECT COUNT(*) FROM venue").fetchone()[0]
            return jsonify(status="ok", venues=venues), 200
        except Exception:
            app.logger.exception("Health check database failure")
            return jsonify(status="error", error="Database connection failure"), 503

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
