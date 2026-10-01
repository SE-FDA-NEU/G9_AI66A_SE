"""Flask web app - Sports Venue Booking System.

Walking skeleton (Sprint 2): GET /search reads the venue table and renders it.
Run from the repository root:  python src/app.py
"""
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from db import connect

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


def create_app(database=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only")
    app.config["DATABASE"] = database

    @app.route("/health")
    def health():
        # Used by docs/SETUP.md: proves the app can reach the database.
        with connect(app.config["DATABASE"]) as conn:
            venues = conn.execute("SELECT COUNT(*) FROM venue").fetchone()[0]
        return jsonify(status="ok", venues=venues)

    @app.route("/")
    @app.route("/search")
    def search():
        sport = request.args.get("sport", "").strip()
        area = request.args.get("area", "").strip()
        with connect(app.config["DATABASE"]) as conn:
            venues = conn.execute(SEARCH_SQL, {"sport": sport, "area": area}).fetchall()
            areas = [r[0] for r in conn.execute("SELECT DISTINCT area FROM venue ORDER BY area")]
            total = conn.execute("SELECT COUNT(*) FROM venue").fetchone()[0]
        return render_template("search.html", venues=venues, sports=SPORTS, areas=areas,
                               sport=sport, area=area, total=total)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
