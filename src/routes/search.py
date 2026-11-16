"""Search for venues (US03): the home page, /search and GET /api/venues."""
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request

import venues
from db import get_db
from errors import BusinessRuleError

bp = Blueprint("search", __name__)


def filters():
    return {
        k: request.args.get(k, "").strip()
        for k in ("sport", "area", "q", "sort", "min_price", "max_price", "date", "hour")
    }


@bp.get("/")
@bp.get("/search")
def search_page():
    now = current_app.config.get("NOW", datetime.now)()
    chosen = filters()
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM venue WHERE active = 1").fetchone()[0]
    try:
        results = venues.search(conn, now=now, **chosen)
    except BusinessRuleError as err:
        return render_template("search.html", venues=[], error=err.message, total=total,
                               sports=venues.SPORTS, areas=venues.AREAS,
                               today=now.date().isoformat(), **chosen), err.status
    return render_template("search.html", venues=results, error=None, total=total,
                           sports=venues.SPORTS, areas=venues.AREAS,
                           today=now.date().isoformat(), **chosen)


@bp.get("/api/venues")
def api_search():
    now = current_app.config.get("NOW", datetime.now)()
    results = venues.search(get_db(), now=now, **filters())
    body = {"venues": [dict(v) for v in results]}
    if not results:
        body["message"] = venues.NO_MATCH                            # BR9
    return jsonify(body)
