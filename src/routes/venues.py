"""Venue detail and availability (US04): /venues/<id> and GET /api/venues/<id>."""
from collections import Counter
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request, send_from_directory

import venues
from db import get_db
from errors import BusinessRuleError

bp = Blueprint("venues", __name__)


@bp.get("/venues/<int:venue_id>")
def venue_page(venue_id):
    conn = get_db()
    venue = venues.get_venue(conn, venue_id)
    day = request.args.get("date") or datetime.now().date().isoformat()
    return render_template("venue.html", venue=venue, photos=venues.photos(conn, venue_id), day=day,
                           today=datetime.now().date().isoformat())


@bp.get("/venues/<int:venue_id>/photos/<int:photo_id>")
def venue_photo(venue_id, photo_id):
    photo = get_db().execute("SELECT file_name FROM venue_photo WHERE id = ? AND venue_id = ?",
                             (photo_id, venue_id)).fetchone()
    if photo is None:
        raise BusinessRuleError(404, "Photo not found.")
    return send_from_directory(current_app.config["UPLOAD_DIR"], photo["file_name"])


@bp.get("/api/venues/<int:venue_id>")
def api_venue(venue_id):
    conn = get_db()
    now = datetime.now()
    venue = venues.get_venue(conn, venue_id)
    day = venues.parse_day(request.args.get("date") or now.date().isoformat(), now)
    slots = venues.day_slots(conn, venue, day, now)
    counts = Counter(s["status"] for s in slots)
    return jsonify(venue=dict(venue), date=day.isoformat(), slots=slots,
                   free=counts["free"], booked=counts["booked"], blocked=counts["blocked"])
