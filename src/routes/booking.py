"""Booking pages and API (US05, issue #68).

/booking/<venue_id>   GET: pick date, start and hours, see the segmented price; POST: confirm
/bookings/<code>      the confirmation page - own bookings only (BR14)
/api/bookings         POST, design.md section 3 row 6

The signed-in user is read from session["user_id"], which the login route (#64) sets.
"""
from datetime import date, datetime

from flask import (Blueprint, current_app, flash, g, jsonify, redirect, render_template, request,
                   session, url_for)

import booking as svc
import reviews
from db import connect
from errors import BusinessRuleError

bp = Blueprint("booking", __name__)


def _now():
    # Tests pin the clock through app.config["NOW"] so their dates never fall into the past.
    return current_app.config.get("NOW", datetime.now)()


def _connect():
    return connect(current_app.config["DATABASE"])


def _current_user(conn):
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return conn.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()


def _booking_page(conn, user, venue_id, form, error=None, status=200):
    """Render /booking/<venue_id> for the date and choice in `form` (query or posted form)."""
    now = _now()
    venue = svc.get_venue(conn, venue_id)
    try:
        day = date.fromisoformat(form.get("date") or now.date().isoformat())
    except ValueError:
        day, error, status = now.date(), error or "Choose a valid date", 400
    free = svc.free_hours(conn, venue, day, now)
    nearest = None if free else svc.nearest_free_day(conn, venue, day, now)
    start, hours = form.get("start_hour", ""), form.get("hours", "")

    quote = None
    if user["email_verified_at"] is None and error is None:
        # BR4: say it before the customer fills the form, not only after they confirm
        error, status = "Please verify your email before booking", 403
    elif start and hours and error is None:
        try:
            v, d, s, h = svc.check_request(conn, user, venue_id, day, start, hours, now)
            quote = svc.quote(conn, v["id"], d, s, h)
        except BusinessRuleError as e:
            error, status = e.message, e.status

    return render_template("booking.html", venue=venue, day=day, free=free, nearest=nearest,
                           start=start, hours=hours, quote=quote, error=error,
                           max_hours=svc.MAX_HOURS), status


@bp.route("/booking/<int:venue_id>", methods=["GET", "POST"])
def booking_page(venue_id):
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return redirect("/login?next=" + request.path)
        try:
            if request.method == "GET":
                return _booking_page(conn, user, venue_id, request.args)
            f = request.form
            result = svc.create_booking(conn, user, venue_id, f.get("date"), f.get("start_hour"),
                                        f.get("hours"), _now())
            return redirect(url_for("booking.booking_detail", code=result["code"]))
        except BusinessRuleError as e:
            if e.status == 404:
                return render_template("booking.html", venue=None, error=e.message), 404
            # Keep the date and the choice, drop the quote: the slot may be gone (BR11)
            return _booking_page(conn, user, venue_id, request.form, e.message, e.status)


@bp.route("/bookings/<code>")
def booking_detail(code):
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return redirect("/login?next=" + request.path)
        try:
            booking, segs = svc.find_for_customer(conn, code, user)
        except BusinessRuleError as e:
            return render_template("booking_done.html", booking=None, error=e.message), e.status
    return render_template("booking_done.html", booking=booking, segments=segs, error=None)


@bp.route("/api/bookings", methods=["POST"])
def api_create_booking():
    data = request.get_json(silent=True) or request.form
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return jsonify(error="Please sign in to book a venue", rule="BR14"), 401
        try:
            result = svc.create_booking(conn, user, data.get("venue_id"), data.get("date"),
                                        data.get("start_hour"), data.get("hours"), _now())
        except BusinessRuleError as e:
            return jsonify(e.as_json()), e.status
    return jsonify(result), 201


@bp.route("/my-bookings")
def my_bookings():
    """Customer views their booking history (US20, BR14)."""
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return redirect("/login?next=" + request.path)
        status_filter = request.args.get("status")
        bookings = svc.list_for_customer(conn, user["id"], status_filter=status_filter)
        return render_template("my_bookings.html", bookings=bookings,
                               current_filter=status_filter or "all", now=_now())


@bp.route("/my-bookings/<code>/cancel", methods=["POST"])
@bp.route("/bookings/<code>/cancel", methods=["POST"])
def cancel_booking_route(code):
    """Customer cancels an upcoming booking with refund policy (US19, BR14, BR15)."""
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return redirect("/login?next=" + request.path)
        try:
            res = svc.cancel_booking(conn, code, user, _now())
            flash(res["message"], "success")
        except BusinessRuleError as e:
            flash(e.message, "error")
            if e.status == 403:
                return render_template("error.html", error=e.message), 403
    return redirect("/my-bookings")


@bp.route("/api/bookings/my-history")
def api_my_history():
    """API for customer booking history (US20)."""
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return jsonify(error="Please sign in", rule="BR14"), 401
        status = request.args.get("status")
        bookings = svc.list_for_customer(conn, user["id"], status)
        return jsonify(bookings=[dict(b) for b in bookings])


@bp.route("/api/bookings/<code>/cancel", methods=["POST"])
def api_cancel_booking(code):
    """API for booking cancellation (US19)."""
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return jsonify(error="Please sign in", rule="BR14"), 401
        try:
            res = svc.cancel_booking(conn, code, user, _now())
            return jsonify(res), 200
        except BusinessRuleError as e:
            return jsonify(e.as_json()), e.status


@bp.route("/my-bookings/<code>/review", methods=["POST"])
def submit_review_route(code):
    """Customer submits a review for a completed booking (US12, BR18)."""
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return redirect("/login?next=" + request.path)
        rating = request.form.get("rating")
        comment = request.form.get("comment")
        try:
            reviews.submit_review(conn, code, user, rating, comment)
            flash("Thank you for submitting your review!", "success")
        except BusinessRuleError as e:
            flash(e.message, "error")
    return redirect("/my-bookings")



