"""Flask web app - Sports Venue Booking System.

Run from the repository root:  python src/app.py
Pages live in src/routes/ (one module per group of screens); business rules live in the
service modules (src/auth.py, ...). This file only wires them together.
"""
import importlib
import os
import pkgutil

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

import routes
from db import close_db, get_db
from errors import BusinessRuleError
from guards import SESSION_TIMEOUT, load_user

load_dotenv()

SPORTS = ["Football", "Badminton", "Tennis", "Pickleball"]

# BR9: sport AND area must both match; an empty filter means "any".
SEARCH_SQL = """
SELECT v.id, v.name, v.sport, v.area, v.address, v.hourly_price, v.open_hour, v.close_hour
FROM venue v
WHERE v.active = 1
  AND (:sport = '' OR v.sport = :sport)
  AND (:area  = '' OR v.area  = :area)
ORDER BY v.area, v.sport, v.name
"""


def wants_json():
    return request.path.startswith("/api/")


def create_app(database=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only")
    app.config["DATABASE"] = database
    app.config["PERMANENT_SESSION_LIFETIME"] = SESSION_TIMEOUT        # BR8

    app.before_request(load_user)
    app.teardown_appcontext(close_db)
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

    @app.route("/health")
    def health():
        # Used by docs/SETUP.md: proves the app can reach the database.
        venues = get_db().execute("SELECT COUNT(*) FROM venue").fetchone()[0]
        return jsonify(status="ok", venues=venues)

    @app.route("/")
    @app.route("/search")
    def search():
        sport = request.args.get("sport", "").strip()
        area = request.args.get("area", "").strip()
        conn = get_db()
        venues = conn.execute(SEARCH_SQL, {"sport": sport, "area": area}).fetchall()
        areas = [r[0] for r in conn.execute("SELECT DISTINCT area FROM venue ORDER BY area")]
        total = conn.execute("SELECT COUNT(*) FROM venue").fetchone()[0]
        return render_template("search.html", venues=venues, sports=SPORTS, areas=areas,
                               sport=sport, area=area, total=total)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
