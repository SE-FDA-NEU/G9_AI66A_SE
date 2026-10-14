"""Search for venues (US03): the home page, /search and GET /api/venues."""
from flask import Blueprint, jsonify, render_template, request

import venues
from db import get_db
from errors import BusinessRuleError

bp = Blueprint("search", __name__)


def filters():
    return {k: request.args.get(k, "").strip() for k in ("sport", "area", "q")}


@bp.get("/")
@bp.get("/search")
def search_page():
    chosen = filters()
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM venue WHERE active = 1").fetchone()[0]
    try:
        results = venues.search(conn, **chosen)
    except BusinessRuleError as err:
        return render_template("search.html", venues=[], error=err.message, total=total,
                               sports=venues.SPORTS, areas=venues.AREAS, **chosen), err.status
    return render_template("search.html", venues=results, error=None, total=total,
                           sports=venues.SPORTS, areas=venues.AREAS, **chosen)


@bp.get("/api/venues")
def api_search():
    results = venues.search(get_db(), **filters())
    body = {"venues": [dict(v) for v in results]}
    if not results:
        body["message"] = venues.NO_MATCH                            # BR9
    return jsonify(body)
