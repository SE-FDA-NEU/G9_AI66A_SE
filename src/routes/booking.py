"""Booking pages and API (US05, issue #68).

/booking/<venue_id>   GET: pick date, start and hours, see the segmented price; POST: confirm
/bookings/<code>      the confirmation page - own bookings only (BR14)
/api/bookings         POST, design.md section 3 row 6

The signed-in user is read from session["user_id"], which the login route (#64) sets.
"""
from datetime import date, datetime
from urllib.parse import quote as url_quote

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import booking as svc
import payment
import reviews
import venues
from db import connect
from errors import BusinessRuleError
from time_utils import vn_now

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
    user = conn.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()
    if user and user["suspended"]:
        session.clear()
        g.account_suspended = True
        return None
    return user


def _unauthenticated_html():
    if getattr(g, "account_suspended", False):
        flash("Your account has been suspended", "error")
        return redirect("/login")
    return redirect("/login?next=" + url_quote(request.full_path.rstrip("?"), safe="/"))


def _unauthenticated_json(default_message):
    if getattr(g, "account_suspended", False):
        raise BusinessRuleError(403, "Your account has been suspended", "BR14")
    return jsonify(error=default_message, rule="BR14"), 401


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
            return _unauthenticated_html()
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
            return _unauthenticated_html()
        try:
            booking, segs = svc.find_for_customer(conn, code, user)
        except BusinessRuleError as e:
            return render_template("booking_done.html", booking=None, error=e.message), e.status
    return render_template("booking_done.html", booking=booking, segments=segs, error=None)


@bp.route("/api/bookings", methods=["POST"])
def api_create_booking():
    if request.is_json:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise BusinessRuleError(400, "Invalid JSON payload")
    else:
        data = request.form
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return _unauthenticated_json("Please sign in to book a venue")
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
            return _unauthenticated_html()
        status_filter = request.args.get("status")
        now = _now()
        bookings = svc.list_for_customer(conn, user["id"], status_filter=status_filter, now=now)
        counts = svc.status_counts(conn, user["id"], now=now)
        enriched = []
        for b in bookings:
            d = dict(b)
            try:
                start_dt = datetime.strptime(str(b["start_at"])[:16], "%Y-%m-%d %H:%M")
                end_dt = datetime.strptime(str(b["end_at"])[:16], "%Y-%m-%d %H:%M")
                diff_hours = (start_dt - now).total_seconds() / 3600.0
            except (ValueError, TypeError):
                start_dt = now
                end_dt = now
                diff_hours = 0

            if b["status"] == "confirmed":
                if now >= end_dt:
                    d["match_state"] = "completed"
                    d["can_cancel"] = False
                elif start_dt <= now < end_dt:
                    d["match_state"] = "in_progress"
                    d["can_cancel"] = False
                elif diff_hours < 2:
                    d["match_state"] = "starting_soon"
                    d["can_cancel"] = False
                elif diff_hours >= 24:
                    d["match_state"] = "upcoming"
                    d["can_cancel"] = True
                    d["refund_pct"] = 100
                else:
                    d["match_state"] = "upcoming"
                    d["can_cancel"] = True
                    d["refund_pct"] = 50
            else:
                d["match_state"] = b["status"]
                d["can_cancel"] = False
            enriched.append(d)

        return render_template("my_bookings.html", bookings=enriched,
                               current_filter=status_filter or "all", counts=counts, now=now)


@bp.route("/my-bookings/<code>/cancel", methods=["POST"])
@bp.route("/bookings/<code>/cancel", methods=["POST"])
def cancel_booking_route(code):
    """Customer cancels an upcoming booking with refund policy (US19, BR14, BR15)."""
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return _unauthenticated_html()
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
            return _unauthenticated_json("Please sign in")
        status = request.args.get("status")
        bookings = svc.list_for_customer(conn, user["id"], status, now=_now())
        return jsonify(bookings=[dict(b) for b in bookings])


@bp.route("/api/bookings/<code>/cancel", methods=["POST"])
def api_cancel_booking(code):
    """API for booking cancellation (US19)."""
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return _unauthenticated_json("Please sign in")
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
            return _unauthenticated_html()
        rating = request.form.get("rating")
        comment = request.form.get("comment")
        try:
            reviews.submit_review(
                conn,
                code,
                user,
                rating,
                comment,
                now=current_app.config.get("NOW", vn_now)(),
            )
            flash("Thank you for submitting your review!", "success")
        except BusinessRuleError as e:
            flash(e.message, "error")
    return redirect("/my-bookings")


@bp.get("/api/quote/<int:venue_id>")
def api_quote(venue_id):
    """Return segmented price quote for a venue, date, start_hour, and hours (BR12)."""
    now = _now()
    with _connect() as conn:
        venue = venues.get_venue(conn, venue_id)
        day_str = request.args.get("date") or now.date().isoformat()
        day = venues.parse_day(day_str, now)
        try:
            start_hour = int(request.args.get("start_hour", ""))
            hours = int(request.args.get("hours", ""))
        except (TypeError, ValueError):
            raise BusinessRuleError("BR11", "Choose a start time and a number of hours", 400)
        if not 1 <= hours <= svc.MAX_HOURS:
            raise BusinessRuleError("BR11", "A booking is 1 to 4 consecutive hours", 400)
        if not venue["open_hour"] <= start_hour < venue["close_hour"]:
            raise BusinessRuleError(
                "BR11",
                f"Start time must be between {venue['open_hour']:02d}:00 and {venue['close_hour'] - 1:02d}:00",
                400,
            )
        if start_hour + hours > venue["close_hour"]:
            raise BusinessRuleError(
                "BR11",
                f"The venue closes at {venue['close_hour']:02d}:00 - from {start_hour:02d}:00 you can"
                f" book at most {venue['close_hour'] - start_hour} hour(s)",
                400,
            )
        wanted = []
        for h in range(start_hour, start_hour + hours):
            if datetime(day.year, day.month, day.day, h) <= now:
                raise BusinessRuleError(400, "This time slot is in the past", "BR11")
            wanted.append(svc.slot_key(day, h))
        marks = ",".join("?" * len(wanted))
        if (
            conn.execute(
                f"SELECT 1 FROM blocked_slot WHERE venue_id = ? AND slot_start IN ({marks})",
                (venue_id, *wanted),
            ).fetchone()
            or conn.execute(
                f"SELECT 1 FROM booking_slot WHERE venue_id = ? AND slot_start IN ({marks})",
                (venue_id, *wanted),
            ).fetchone()
        ):
            raise BusinessRuleError(409, "This time slot is no longer available", "BR11")
        q = svc.quote(conn, venue["id"], day, start_hour, hours)
        segments = [
            {**seg, "is_peak": seg["price_per_hour"] != venue["hourly_price"]}
            for seg in q["segments"]
        ]
        return jsonify(
            venue_id=venue_id,
            date=day.isoformat(),
            start_hour=start_hour,
            hours=hours,
            total_price=q["total_price"],
            segments=segments,
        )


def _ics_escape(value):
    return str(value).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _ics_dt(dt_str):
    dt = datetime.strptime(str(dt_str)[:16], "%Y-%m-%d %H:%M")
    return dt.strftime("%Y%m%dT%H%M%S")


@bp.get("/my-bookings/<code>/ics")
def booking_ics(code):
    """Download an RFC 5545 .ics calendar invite for a customer's booking (BR14)."""
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return _unauthenticated_html()
        booking, _segs = svc.find_for_customer(conn, code, user)
        now_stamp = _now().strftime("%Y%m%dT%H%M%S")
        status = "CANCELLED" if booking["status"] == "cancelled" else "CONFIRMED"
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Sports Venue Booking//G9_AI66A_SE//EN",
            "CALSCALE:GREGORIAN",
            "BEGIN:VEVENT",
            f"UID:{booking['code']}@sports-venue-booking",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;TZID=Asia/Ho_Chi_Minh:{_ics_dt(booking['start_at'])}",
            f"DTEND;TZID=Asia/Ho_Chi_Minh:{_ics_dt(booking['end_at'])}",
            f"SUMMARY:{_ics_escape(booking['venue_name'])} ({_ics_escape(booking['sport'])}) - {booking['code']}",
            f"LOCATION:{_ics_escape(booking['address'])}",
            f"DESCRIPTION:Booking {booking['code']} | Total: {booking['total_price']} VND",
            f"STATUS:{status}",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
        body = "\r\n".join(lines) + "\r\n"
        return Response(
            body,
            mimetype="text/calendar; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="booking-{booking["code"]}.ics"'},
        )


@bp.route("/booking/<int:venue_id>/checkout", methods=["POST"])
def payment_checkout_create(venue_id):
    """Create a QR payment session for a booking request and redirect to checkout."""
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return _unauthenticated_html()
        f = request.form
        try:
            sess = payment.create_session(
                conn, user, venue_id, f.get("date"), f.get("start_hour"), f.get("hours"), _now()
            )
            return redirect(url_for("booking.payment_checkout", token=sess["token"]))
        except BusinessRuleError as e:
            if e.status == 404:
                return render_template("booking.html", venue=None, error=e.message), 404
            return _booking_page(conn, user, venue_id, request.form, e.message, e.status)


@bp.route("/payment/<token>", methods=["GET"])
def payment_checkout(token):
    """Render the QR payment checkout page for a payment session."""
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return _unauthenticated_html()
        try:
            sess = payment.get_session(conn, token, user)
        except BusinessRuleError as e:
            return render_template("error.html", error=e.message), e.status
    scan_url = url_for("booking.payment_scan", token=token, _external=True)
    return render_template(
        "payment_checkout.html",
        pay=sess,
        qr_svg=payment.generate_qr_svg(scan_url),
        scan_url=scan_url,
        error=None,
    )


@bp.route("/payment/<token>/scan", methods=["GET", "POST"])
def payment_scan(token):
    """Simulated QR scanner page where the user enters the exact amount to pay."""
    with _connect() as conn:
        if request.method == "GET":
            try:
                sess = payment.get_session(conn, token)
            except BusinessRuleError as e:
                return render_template("error.html", error=e.message), e.status
            already_accepted = sess["status"] in ("accepted", "paid", "refunded", "partially_refunded")
            return render_template(
                "payment_scan.html",
                pay=sess,
                accepted=already_accepted,
                otp_code=sess["otp_code"] if already_accepted else None,
                error=None,
            )

        try:
            sess = payment.accept_qr_payment(conn, token, request.form.get("amount", ""))
            return render_template(
                "payment_scan.html",
                pay=sess,
                accepted=True,
                otp_code=sess["otp_code"],
                error=None,
            )
        except BusinessRuleError as e:
            if e.status == 404:
                return render_template("error.html", error=e.message), 404
            sess = payment.get_session(conn, token)
            return render_template(
                "payment_scan.html",
                pay=sess,
                accepted=False,
                otp_code=None,
                error=e.message,
            ), e.status


@bp.route("/payment/<token>/confirm", methods=["POST"])
def payment_confirm(token):
    """Verify OTP and finalize the booking."""
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return _unauthenticated_html()
        try:
            result = payment.confirm_and_book(
                conn, token, user, request.form.get("otp_code", ""), _now()
            )
            return redirect(url_for("booking.booking_detail", code=result["code"]))
        except BusinessRuleError as e:
            if e.status in (403, 404):
                return render_template("error.html", error=e.message), e.status
            sess = payment.get_session(conn, token, user)
            scan_url = url_for("booking.payment_scan", token=token, _external=True)
            return render_template(
                "payment_checkout.html",
                pay=sess,
                qr_svg=payment.generate_qr_svg(scan_url),
                scan_url=scan_url,
                error=e.message,
            ), e.status


@bp.route("/api/payment/<token>/status", methods=["GET"])
def api_payment_status(token):
    """Poll payment session status (pending/accepted/paid) for the owning customer."""
    with _connect() as conn:
        user = _current_user(conn)
        if user is None:
            return _unauthenticated_json("Please sign in")
        try:
            s = payment.get_session(conn, token, user)
            return jsonify(
                status=s["status"],
                paid_amount=s["paid_amount"],
                booking_code=s["booking_code"],
            )
        except BusinessRuleError as e:
            return jsonify(e.as_json()), e.status




