"""The venue management area (US06, US09, US10): owner's venue list, schedule, and bookings.
Only owners get in (BR7, BR14, BR18); a customer gets 403."""
from datetime import date, datetime

from flask import Blueprint, Response, current_app, flash, g, jsonify, redirect, render_template, request

import owner_analytics
import venues
import pricing
from db import get_db
from errors import BusinessRuleError
from guards import login_required

bp = Blueprint("owner", __name__)

HOURS = list(range(0, 25))

WEEKDAY_PRESETS = {
    "all": (range(7), "all weekdays"),
    "weekdays": (range(0, 5), "weekdays (Mon-Fri)"),
    "weekends": (range(5, 7), "weekends (Sat-Sun)"),
}


@bp.get("/owner/venues")
@login_required("owner")
def venue_list():
    conn = get_db()
    return render_template(
        "owner_venues.html",
        venues=venues.owner_venues(conn, g.user),
        summary=owner_analytics.get_owner_summary(conn, g.user["id"]),
        sports=venues.SPORTS,
        areas=venues.AREAS,
        hours=HOURS,
    )


@bp.post("/owner/venues/<int:venue_id>/edit")
@login_required("owner")
def edit_venue_route(venue_id):
    """Update venue operating hours, standard hourly rate, and details (BR9, BR13, BR14)."""
    conn = get_db()
    next_url = (request.form.get("next") or "").strip()
    if not next_url.startswith("/owner/") or "//" in next_url:
        next_url = "/owner/venues"
    try:
        venues.update_venue(conn, g.user, venue_id, request.form)
        flash("Venue settings updated successfully.", "success")
    except BusinessRuleError as e:
        flash(e.message, "error")
    return redirect(next_url)


@bp.post("/api/owner/venues/<int:venue_id>/edit")
@login_required("owner")
def api_edit_venue(venue_id):
    """API for updating a venue's operating hours, base rate, and details."""
    data = request.get_json(silent=True)
    if data is None:
        data = request.form.to_dict()
    try:
        updated = venues.update_venue(get_db(), g.user, venue_id, data)
        return jsonify(venue=dict(updated), status="updated"), 200
    except BusinessRuleError as e:
        return jsonify(e.as_json()), e.status


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
    values, problems = venues.check_new_venue(
        {k: str(v) if v is not None else "" for k, v in data.items()}
    )
    if problems:
        raise problems[0]
    return jsonify(venue_id=venues.create_venue(get_db(), g.user, values)), 201


@bp.get("/owner/bookings")
@login_required("owner")
def owner_bookings_page():
    """Venue owner views bookings across their venues (US23, BR16, BR17, BR18)."""
    now = current_app.config.get("NOW", datetime.now)()
    date_str = request.args.get("date") or now.date().isoformat()
    try:
        date.fromisoformat(date_str)
    except ValueError:
        flash("Please choose a valid date in YYYY-MM-DD format.", "error")
        date_str = now.date().isoformat()
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
    day_prices = pricing.hour_prices(conn, venue_id, day)
    rules = pricing.list_pricing_rules(conn, venue_id)
    return render_template(
        "owner_schedule.html",
        venue=venue,
        day=day,
        day_str=day_str,
        slots=slots,
        hour_prices=day_prices,
        pricing_rules=rules,
        weekdays=pricing.WEEKDAYS,
        hours=list(range(venue["open_hour"], venue["close_hour"] + 1)),
        all_hours=HOURS,
        sports=venues.SPORTS,
        areas=venues.AREAS,
        now=now,
    )


@bp.post("/owner/venues/<int:venue_id>/schedule/block")
@login_required("owner")
def block_slot_route(venue_id):
    """Block a slot for maintenance (US22)."""
    now = current_app.config.get("NOW", datetime.now)()
    conn = get_db()
    day_str = request.form.get("date")
    reason = (request.form.get("reason") or "").strip() or "Maintenance"
    try:
        day = date.fromisoformat(day_str or "")
        hour = int(request.form.get("hour"))
        venues.block_single_slot(conn, g.user, venue_id, day, hour, reason, now)
        flash(f"Slot {hour:02d}:00-{hour + 1:02d}:00 blocked successfully.", "success")
    except (TypeError, ValueError):
        flash("Invalid date or hour.", "error")
        return redirect(f"/owner/venues/{venue_id}/schedule")
    except BusinessRuleError as e:
        flash(e.message, "error")

    return redirect(f"/owner/venues/{venue_id}/schedule?date={day_str}")


@bp.post("/owner/venues/<int:venue_id>/schedule/unblock")
@login_required("owner")
def unblock_slot_route(venue_id):
    """Unblock a slot (US22, BR13)."""
    conn = get_db()
    day_str = request.form.get("date")
    try:
        day = date.fromisoformat(day_str or "")
        hour = int(request.form.get("hour"))
        venues.unblock_single_slot(conn, g.user, venue_id, day, hour)
        flash(f"Slot {hour:02d}:00-{hour + 1:02d}:00 unblocked successfully.", "success")
    except (TypeError, ValueError):
        flash("Invalid date or hour.", "error")
        return redirect(f"/owner/venues/{venue_id}/schedule")
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
        start_date = date.fromisoformat(request.form.get("start_date") or "")
        end_date = date.fromisoformat(request.form.get("end_date") or "")
        start_hour = int(request.form.get("start_hour"))
        end_hour = int(request.form.get("end_hour"))
        reason = (request.form.get("reason") or "").strip() or "Maintenance"

        blocked_count, skipped = venues.batch_block_slots(
            conn, g.user, venue_id, start_date, end_date, start_hour, end_hour, reason, now
        )

        if skipped:
            msg = f"Blocked {blocked_count} slot(s). Skipped {len(skipped)} already booked slot(s): {', '.join(skipped)}"
        else:
            msg = f"Blocked {blocked_count} slot(s) successfully"

        flash(msg, "success")
        return redirect(f"/owner/venues/{venue_id}/schedule?date={start_date.isoformat()}")
    except BusinessRuleError as e:
        flash(e.message, "error")
        return redirect(f"/owner/venues/{venue_id}/schedule")
    except (TypeError, ValueError):
        flash("Invalid date or hour range.", "error")
        return redirect(f"/owner/venues/{venue_id}/schedule")


@bp.get("/api/owner/bookings")
@login_required("owner")
def api_owner_bookings():
    """API for owner bookings (US23)."""
    now = current_app.config.get("NOW", datetime.now)()
    date_str = request.args.get("date") or now.date().isoformat()
    try:
        date.fromisoformat(date_str)
    except ValueError:
        return jsonify(error="Invalid date format, expected YYYY-MM-DD"), 400
    venue_id = request.args.get("venue_id", type=int)
    booking_list = venues.owner_bookings(get_db(), g.user, date_str, venue_id=venue_id)
    return jsonify(bookings=[dict(b) for b in booking_list])


@bp.post("/api/owner/venues/<int:venue_id>/block")
@login_required("owner")
def api_block_slot(venue_id):
    """API for blocking a slot (US22)."""
    now = current_app.config.get("NOW", datetime.now)()
    data = request.get_json(silent=True) or request.form
    try:
        day = date.fromisoformat(str(data.get("date") or ""))
        hour = int(data.get("hour"))
    except (TypeError, ValueError):
        return jsonify(error="Invalid date or hour"), 400
    reason = (data.get("reason") or "").strip() or "Maintenance"
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
    try:
        day = date.fromisoformat(str(data.get("date") or ""))
        hour = int(data.get("hour"))
    except (TypeError, ValueError):
        return jsonify(error="Invalid date or hour"), 400
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
        all_hours=HOURS,
        sports=venues.SPORTS,
        areas=venues.AREAS,
    )


def _safe_owner_redirect(venue_id, default_path):
    """Allow safe relative redirects within this venue's owner pages."""
    next_url = (request.form.get("next") or "").strip()
    prefix = f"/owner/venues/{venue_id}/"
    if next_url.startswith(prefix) and "//" not in next_url:
        return next_url
    return default_path


@bp.post("/owner/venues/<int:venue_id>/pricing")
@login_required("owner")
def add_pricing_rule_route(venue_id):
    """Add peak pricing rule (US11, BR12)."""
    conn = get_db()
    target = _safe_owner_redirect(venue_id, f"/owner/venues/{venue_id}/pricing")
    try:
        venues.check_venue_owner(conn, venue_id, g.user["id"])
        raw_weekday = (request.form.get("weekday") or "").strip()
        start_hour = int(request.form.get("start_hour"))
        end_hour = int(request.form.get("end_hour"))
        price_per_hour = venues.parse_price(request.form.get("price_per_hour") or "")
        if price_per_hour is None:
            raise ValueError("invalid price")

        if raw_weekday in WEEKDAY_PRESETS:
            days_iter, label = WEEKDAY_PRESETS[raw_weekday]
            added = 0
            skipped = 0
            for wd in days_iter:
                try:
                    pricing.add_pricing_rule(conn, venue_id, wd, start_hour, end_hour, price_per_hour)
                    added += 1
                except BusinessRuleError as exc:
                    if exc.status == 409:
                        skipped += 1
                    else:
                        raise
            if added == 0:
                if raw_weekday == "all":
                    flash("All weekdays already have an overlapping pricing rule for this time range.", "error")
                else:
                    flash(f"Selected {label} already have an overlapping pricing rule for this time range.", "error")
            elif skipped:
                flash(f"Added pricing rule to {added} weekday(s); skipped {skipped} overlapping day(s).", "success")
            else:
                flash(f"Pricing rule added for {label}!", "success")
        else:
            weekday = int(raw_weekday)
            pricing.add_pricing_rule(conn, venue_id, weekday, start_hour, end_hour, price_per_hour)
            flash("Peak pricing rule added successfully!", "success")
    except (TypeError, ValueError):
        flash("Please enter valid numbers for weekday, hours, and price.", "error")
    except BusinessRuleError as e:
        flash(e.message, "error")

    return redirect(target)


@bp.post("/owner/venues/<int:venue_id>/pricing/<int:rule_id>/edit")
@login_required("owner")
def edit_pricing_rule_route(venue_id, rule_id):
    """Update an existing peak pricing rule (US11, BR12, BR13)."""
    conn = get_db()
    target = _safe_owner_redirect(venue_id, f"/owner/venues/{venue_id}/pricing")
    try:
        venues.check_venue_owner(conn, venue_id, g.user["id"])
        weekday = int(request.form.get("weekday"))
        start_hour = int(request.form.get("start_hour"))
        end_hour = int(request.form.get("end_hour"))
        price_per_hour = venues.parse_price(request.form.get("price_per_hour") or "")
        if price_per_hour is None:
            raise ValueError("invalid price")
        pricing.update_pricing_rule(conn, venue_id, rule_id, weekday, start_hour, end_hour, price_per_hour)
        flash("Pricing rule updated successfully!", "success")
    except (TypeError, ValueError):
        flash("Please enter valid numbers for weekday, hours, and price.", "error")
    except BusinessRuleError as e:
        flash(e.message, "error")

    return redirect(target)


@bp.post("/owner/venues/<int:venue_id>/pricing/<int:rule_id>/delete")
@login_required("owner")
def delete_pricing_rule_route(venue_id, rule_id):
    """Delete peak pricing rule (US11)."""
    conn = get_db()
    target = _safe_owner_redirect(venue_id, f"/owner/venues/{venue_id}/pricing")
    try:
        venues.check_venue_owner(conn, venue_id, g.user["id"])
        pricing.delete_pricing_rule(conn, rule_id, venue_id)
        flash("Pricing rule deleted successfully.", "success")
    except BusinessRuleError as e:
        flash(e.message, "error")

    return redirect(target)


@bp.get("/owner/analytics")
@login_required("owner")
def owner_analytics_page():
    """Owner revenue, booking, and per-venue analytics dashboard (BR14)."""
    summary = owner_analytics.get_owner_summary(get_db(), g.user["id"])
    return render_template("owner_analytics.html", summary=summary)


@bp.get("/owner/bookings/export.csv")
@login_required("owner")
def owner_bookings_export_csv():
    """Download CSV of all bookings across the owner's venues (BR14)."""
    csv_data = owner_analytics.export_owner_bookings_csv(get_db(), g.user["id"])
    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=owner-bookings.csv"},
    )


