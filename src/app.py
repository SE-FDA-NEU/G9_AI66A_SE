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
from db import ROOT, close_db, connect, get_db
from errors import BusinessRuleError
from guards import SESSION_TIMEOUT, load_user
from pg_schema import PG_SCHEMA
from schema import SCHEMA
from time_utils import vn_now

load_dotenv()


def _ensure_schema(database=None):
    """Create tables if they do not exist. Never drops or reseeds data."""
    if os.environ.get("DATABASE_URL"):
        with connect() as conn:
            try:
                conn.execute("SELECT 1 FROM venue LIMIT 1")
                return
            except Exception:
                pass
            from db import POSTGRES_SCHEMA
            with conn._conn.cursor() as cur:
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{POSTGRES_SCHEMA}"')
            conn.executescript(PG_SCHEMA)
            from pg_seed import seed_postgres
            seed_postgres(conn)
        return
    # SQLite: only create the file/schema when it does not exist yet.
    from db import database_path
    path = database_path() if database is None else Path(database)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with connect(path) as conn:
            conn.executescript(SCHEMA)


def wants_json():
    return request.path.startswith("/api/")


def create_app(database=None):
    app = Flask(__name__)
    app.config.setdefault("NOW", vn_now)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only")
    app.config["DATABASE"] = database
    app.config["PERMANENT_SESSION_LIFETIME"] = SESSION_TIMEOUT        # BR8
    app.config["UPLOAD_DIR"] = Path(os.environ.get("UPLOAD_DIR", ROOT / "data" / "uploads"))  # venue photos, git-ignored
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024                   # largest photo upload: 5 MB
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 31536000

    _ensure_schema(database)

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
