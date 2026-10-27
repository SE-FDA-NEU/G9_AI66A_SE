"""The venue management area (US06, US09, US10): owner's venue list, schedule, and bookings.
Only owners get in (BR7, BR14, BR18); a customer gets 403."""
from datetime import date, datetime

from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request

import venues
import pricing
from db import get_db
from errors import BusinessRuleError
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


@bp.get("/owner/bookings")
@login_required("owner")
def owner_bookings_page():
    """Venue owner views bookings across their venues (US23, BR16, BR17, BR18)."""
    now = current_app.config.get("NOW", datetime.now)()
    date_str = request.args.get("date") or now.date().isoformat()
    venue_id = request.args.get("venue_id", type=int)

    conn = get_db()
    my_venues = venues.owner_venues(conn, g.user)
    booking_list = venues.owner_bookings(conn, g.user, date_str, venue_id=venue_id)

    selected_venue = None
    if venue_id:
        selected_venue = next((v for v in my_venues if v["id"] == venue_id), None)

    return render_template(
        "owner_bookings.html",
        bookings=booking_list,
        my_venues=my_venues,
        date_str=date_str,
        venue_id=venue_id,
        selected_venue=selected_venue,
        now=now,
    )


@bp.get("/owner/bookings/<code>")
@login_required("owner")
def owner_booking_detail_page(code):
    """View one booking for owner; 403 if belonging to another owner (US23 AC 6, BR18)."""
    conn = get_db()
    try:
        booking = venues.owner_booking_detail(conn, g.user, code)
        return render_template("owner_booking_detail.html", booking=booking)
    except BusinessRuleError as e:
        return render_template("error.html", error=e.message), e.status


@bp.get("/owner/venues/<int:venue_id>/schedule")
@login_required("owner")
def venue_schedule_page(venue_id):
    """Venue owner manages availability schedule (US22, BR13, BR14, BR15)."""
    now = current_app.config.get("NOW", datetime.now)()
    conn = get_db()
    try:
        venue = venues.check_venue_owner(conn, venue_id, g.user["id"])
    except BusinessRuleError as e:
        return render_template("error.html", error=e.message), e.status

    day_str = request.args.get("date") or now.date().isoformat()
    try:
        day = date.fromisoformat(day_str)
    except ValueError:
        day = now.date()
        day_str = day.isoformat()

    slots = venues.venue_schedule_slots(conn, venue, day, now)
    return render_template(
        "owner_schedule.html",
        venue=venue,
        day=day,
        day_str=day_str,
        slots=slots,
        now=now,
    )


@bp.post("/owner/venues/<int:venue_id>/schedule/block")
@login_required("owner")
def block_slot_route(venue_id):
    """Block a slot for maintenance (US22)."""
    now = current_app.config.get("NOW", datetime.now)()
    conn = get_db()
    day_str = request.form.get("date")
    hour = int(request.form.get("hour"))
    reason = request.form.get("reason", "Under maintenance")
    try:
        day = date.fromisoformat(day_str)
        venues.block_single_slot(conn, g.user, venue_id, day, hour, reason, now)
        flash(f"Slot {hour:02d}:00-{hour + 1:02d}:00 blocked successfully.", "success")
    except BusinessRuleError as e:
        flash(e.message, "error")

    return redirect(f"/owner/venues/{venue_id}/schedule?date={day_str}")


@bp.post("/owner/venues/<int:venue_id>/schedule/unblock")
@login_required("owner")
def unblock_slot_route(venue_id):
    """Unblock a slot (US22, BR13)."""
    conn = get_db()
    day_str = request.form.get("date")
    hour = int(request.form.get("hour"))
    try:
        day = date.fromisoformat(day_str)
        venues.unblock_single_slot(conn, g.user, venue_id, day, hour)
        flash(f"Slot {hour:02d}:00-{hour + 1:02d}:00 unblocked successfully.", "success")
    except BusinessRuleError as e:
        flash(e.message, "error")

    return redirect(f"/owner/venues/{venue_id}/schedule?date={day_str}")


@bp.post("/owner/venues/<int:venue_id>/schedule/batch-block")
@login_required("owner")
def batch_block_route(venue_id):
    """Batch block slots for maintenance (US22 AC 5)."""
    now = current_app.config.get("NOW", datetime.now)()
    conn = get_db()
    try:
        start_date = date.fromisoformat(request.form.get("start_date"))
        end_date = date.fromisoformat(request.form.get("end_date"))
        start_hour = int(request.form.get("start_hour"))
        end_hour = int(request.form.get("end_hour"))
        reason = request.form.get("reason", "Under maintenance")

        blocked_count, skipped = venues.batch_block_slots(
            conn, g.user, venue_id, start_date, end_date, start_hour, end_hour, reason, now
        )

        if skipped:
            msg = f"Blocked {blocked_count} slot(s). Skipped {len(skipped)} already booked slot(s): {', '.join(skipped)}"
        else:
            msg = f"Blocked {blocked_count} slot(s) successfully"

        flash(msg, "success")
        return redirect(f"/owner/venues/{venue_id}/schedule?date={start_date.isoformat()}")
    except Exception as e:
        flash(str(e), "error")
        return redirect(f"/owner/venues/{venue_id}/schedule")


@bp.get("/api/owner/bookings")
@login_required("owner")
def api_owner_bookings():
    """API for owner bookings (US23)."""
    now = current_app.config.get("NOW", datetime.now)()
    date_str = request.args.get("date") or now.date().isoformat()
    venue_id = request.args.get("venue_id", type=int)
    booking_list = venues.owner_bookings(get_db(), g.user, date_str, venue_id=venue_id)
    return jsonify(bookings=[dict(b) for b in booking_list])


@bp.post("/api/owner/venues/<int:venue_id>/block")
@login_required("owner")
def api_block_slot(venue_id):
    """API for blocking a slot (US22)."""
    now = current_app.config.get("NOW", datetime.now)()
    data = request.get_json(silent=True) or request.form
    day = date.fromisoformat(data.get("date"))
    hour = int(data.get("hour"))
    reason = data.get("reason", "Under maintenance")
    try:
        venues.block_single_slot(get_db(), g.user, venue_id, day, hour, reason, now)
        return jsonify(status="blocked", venue_id=venue_id, date=day.isoformat(), hour=hour), 200
    except BusinessRuleError as e:
        return jsonify(e.as_json()), e.status


@bp.post("/api/owner/venues/<int:venue_id>/unblock")
@login_required("owner")
def api_unblock_slot(venue_id):
    """API for unblocking a slot (US22)."""
    data = request.get_json(silent=True) or request.form
    day = date.fromisoformat(data.get("date"))
    hour = int(data.get("hour"))
    try:
        venues.unblock_single_slot(get_db(), g.user, venue_id, day, hour)
        return jsonify(status="unblocked", venue_id=venue_id, date=day.isoformat(), hour=hour), 200
    except BusinessRuleError as e:
        return jsonify(e.as_json()), e.status


@bp.get("/owner/venues/<int:venue_id>/pricing")
@login_required("owner")
def venue_pricing_page(venue_id):
    """Venue owner configures peak-hour pricing (US11, BR12)."""
    conn = get_db()
    try:
        venue = venues.check_venue_owner(conn, venue_id, g.user["id"])
    except BusinessRuleError as e:
        return render_template("error.html", error=e.message), e.status

    rules = pricing.list_pricing_rules(conn, venue_id)
    return render_template(
        "owner_pricing.html",
        venue=venue,
        rules=rules,
        weekdays=pricing.WEEKDAYS,
        hours=list(range(venue["open_hour"], venue["close_hour"] + 1)),
    )


@bp.post("/owner/venues/<int:venue_id>/pricing")
@login_required("owner")
def add_pricing_rule_route(venue_id):
    """Add peak pricing rule (US11, BR12)."""
    conn = get_db()
    try:
        venues.check_venue_owner(conn, venue_id, g.user["id"])
        weekday = int(request.form.get("weekday"))
        start_hour = int(request.form.get("start_hour"))
        end_hour = int(request.form.get("end_hour"))
        price_per_hour = int(request.form.get("price_per_hour").replace(",", "").replace(".", ""))

        pricing.add_pricing_rule(conn, venue_id, weekday, start_hour, end_hour, price_per_hour)
        flash("Peak pricing rule added successfully!", "success")
    except BusinessRuleError as e:
        flash(e.message, "error")
    except Exception as e:
        flash(str(e), "error")

    return redirect(f"/owner/venues/{venue_id}/pricing")


@bp.post("/owner/venues/<int:venue_id>/pricing/<int:rule_id>/delete")
@login_required("owner")
def delete_pricing_rule_route(venue_id, rule_id):
    """Delete peak pricing rule (US11)."""
    conn = get_db()
    try:
        venues.check_venue_owner(conn, venue_id, g.user["id"])
        pricing.delete_pricing_rule(conn, rule_id, venue_id)
        flash("Pricing rule deleted successfully.", "success")
    except BusinessRuleError as e:
        flash(e.message, "error")

    return redirect(f"/owner/venues/{venue_id}/pricing")



