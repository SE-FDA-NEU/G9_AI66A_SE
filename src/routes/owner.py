"""The venue management area (US06): the owner's venue list and the add-venue form.
Only owners get in (BR7, BR14); a customer gets 403."""
from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request

import venues
from db import get_db
from guards import login_required

bp = Blueprint("owner", __name__)

HOURS = list(range(0, 25))


@bp.get("/owner/venues")
@login_required("owner")
def venue_list():
    return render_template("owner_venues.html", venues=venues.owner_venues(get_db(), g.user))


@bp.get("/owner/venues/new")
@login_required("owner")
def new_venue_form():
    return render_template("owner_venue_new.html", form={"open_hour": 6, "close_hour": 22}, errors={},
                           sports=venues.SPORTS, areas=venues.AREAS, hours=HOURS)


@bp.post("/owner/venues/new")
@login_required("owner")
def new_venue_submit():
    photo = request.files.get("photo")
    photo_name = photo.filename if photo else ""
    values, problems = venues.check_new_venue(request.form, photo_name)
    if problems:
        form = {**request.form, "open_hour": values["open_hour"], "close_hour": values["close_hour"]}
        return render_template("owner_venue_new.html", form=form, errors={p.field: p.message for p in problems},
                               sports=venues.SPORTS, areas=venues.AREAS, hours=HOURS), problems[0].status
    conn = get_db()
    venue_id = venues.create_venue(conn, g.user, values)
    if photo_name:
        venues.save_photo(conn, current_app.config["UPLOAD_DIR"], venue_id, photo)
    flash("Venue added successfully!", "success")                     # US06 criterion 1
    return redirect("/owner/venues")


@bp.get("/api/owner/venues")
@login_required("owner")
def api_venue_list():
    return jsonify(venues=[dict(v) for v in venues.owner_venues(get_db(), g.user)])


@bp.post("/api/owner/venues")
@login_required("owner")
def api_create_venue():
    data = request.get_json(silent=True) or {}
    values, problems = venues.check_new_venue({k: str(v) for k, v in data.items()})
    if problems:
        raise problems[0]
    return jsonify(venue_id=venues.create_venue(get_db(), g.user, values)), 201

@bp.get("/venues/<int:venue_id>")
def venue_detail(venue_id):
    conn = get_db()
    venue = conn.execute("SELECT * FROM venue WHERE id = ?", (venue_id,)).fetchone()
    if not venue:
        return "Venue not found", 404
    return f"""
    <html>
    <head><title>{venue['name']}</title></head>
    <body>
        <h1>{venue['name']}</h1>
        <a href="/venues/{venue_id}/photos/">Photos</a>
    </body>
    </html>
    """
