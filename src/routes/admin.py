"""Admin portal routes: dashboard, account governance, venue control, review moderation, and JSON APIs."""
from flask import Blueprint, flash, g, jsonify, redirect, render_template, request

import admin
import venues
from db import get_db
from errors import BusinessRuleError
from guards import login_required

bp = Blueprint("admin", __name__)


VALID_TABS = ("overview", "venues", "accounts", "moderation")


def _str_field(data, key, default=""):
    """Extract a string field from JSON/form payload, raising 400 on non-string values."""
    val = data.get(key, default)
    if val is None:
        return ""
    if not isinstance(val, str):
        raise BusinessRuleError(400, f"Invalid {key}: expected a string", field=key)
    return val


@bp.get("/admin")
@login_required("admin")
def dashboard():
    conn = get_db()
    active_tab = request.args.get("tab", "overview").strip()
    if active_tab not in VALID_TABS:
        active_tab = "overview"
    role = request.args.get("role", "").strip()
    status = request.args.get("status", "").strip()
    q = request.args.get("q", "").strip()
    sport = request.args.get("sport", "").strip()
    area = request.args.get("area", "").strip()
    mod_status = (request.args.get("mod_status") or request.args.get("status") or "").strip()

    filters = {
        "role": role,
        "status": status,
        "q": q,
        "sport": sport,
        "area": area,
        "mod_status": mod_status,
    }

    return render_template(
        "admin.html",
        active_tab=active_tab,
        stats=admin.get_platform_stats(conn),
        sport_breakdown=admin.get_sport_breakdown(conn),
        area_breakdown=admin.get_area_breakdown(conn),
        venue_analytics=admin.get_venue_analytics(conn, sport=sport or None, area=area or None, q=q or None),
        users=admin.list_users(conn, role=role or None, status=status or None, q=q or None),
        moderation_reviews=admin.list_moderation_reviews(conn, mod_status=mod_status or None),
        filters=filters,
        sports=venues.SPORTS,
        areas=venues.AREAS,
        current_user_id=g.user["id"],
    )


@bp.post("/admin/users/create")
@login_required("admin")
def create_user():
    conn = get_db()
    email = request.form.get("email", "")
    password = request.form.get("password", "")
    full_name = request.form.get("full_name", "")
    phone = request.form.get("phone", "")
    role = request.form.get("role", "customer")
    auto_verify = any(v in ("1", "true", "on", "yes") for v in request.form.getlist("auto_verify"))
    try:
        admin.create_user_account(conn, email, password, full_name, phone, role, auto_verify=auto_verify)
        flash(f"Account created for {email.strip().casefold()} ({role}).", "success")
    except BusinessRuleError as err:
        flash(err.message, "error")
    return redirect("/admin?tab=accounts")


@bp.post("/admin/users/<int:user_id>/suspend")
@login_required("admin")
def suspend_user(user_id):
    conn = get_db()
    reason = request.form.get("reason", "")
    try:
        admin.suspend_user(conn, user_id, g.user["id"], reason=reason)
        flash("User account suspended.", "success")
    except BusinessRuleError as err:
        flash(err.message, "error")
    return redirect("/admin?tab=accounts")


@bp.post("/admin/users/<int:user_id>/unsuspend")
@login_required("admin")
def unsuspend_user(user_id):
    conn = get_db()
    try:
        admin.unsuspend_user(conn, user_id)
        flash("User account reactivated.", "success")
    except BusinessRuleError as err:
        flash(err.message, "error")
    return redirect("/admin?tab=accounts")


@bp.post("/admin/venues/<int:venue_id>/toggle")
@login_required("admin")
def toggle_venue(venue_id):
    conn = get_db()
    try:
        is_active = admin.toggle_venue_active(conn, venue_id)
        state = "activated" if is_active else "deactivated"
        flash(f"Venue {state}.", "success")
    except BusinessRuleError as err:
        flash(err.message, "error")
    return redirect("/admin?tab=venues")


@bp.post("/admin/reviews/<int:review_id>/moderate")
@login_required("admin")
def moderate_review(review_id):
    conn = get_db()
    action = request.form.get("action", "")
    try:
        admin.moderate_review(conn, review_id, g.user["id"], action)
        label = "approved and restored" if action.strip().lower() == "approve" else "rejected and hidden"
        flash(f"Review {label}.", "success")
    except BusinessRuleError as err:
        flash(err.message, "error")
    return redirect("/admin?tab=moderation")


# ---------------------------------------------------------------------------
# JSON API endpoints
# ---------------------------------------------------------------------------


@bp.get("/api/admin/stats")
@login_required("admin")
def api_stats():
    conn = get_db()
    return jsonify(
        stats=admin.get_platform_stats(conn),
        sport_breakdown=admin.get_sport_breakdown(conn),
        area_breakdown=admin.get_area_breakdown(conn),
    )


def _json_or_form():
    """Return JSON object payload or form data; reject malformed/non-object JSON with 400."""
    if request.is_json:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise BusinessRuleError(400, "Invalid JSON payload")
        return data
    return request.form


@bp.post("/api/admin/users")
@login_required("admin")
def api_create_user():
    data = _json_or_form()
    email = _str_field(data, "email")
    password = _str_field(data, "password")
    full_name = _str_field(data, "full_name")
    phone = _str_field(data, "phone")
    role = _str_field(data, "role", "customer")
    val = data.get("auto_verify", True)
    auto_verify = val if isinstance(val, bool) else str(val).strip().lower() in ("1", "true", "on", "yes")
    user_id = admin.create_user_account(
        get_db(),
        email=email,
        password=password,
        full_name=full_name,
        phone=phone,
        role=role,
        auto_verify=auto_verify,
    )
    return jsonify(id=user_id, email=email.strip().casefold(), role=role.strip()), 201


@bp.post("/api/admin/users/<int:user_id>/suspend")
@login_required("admin")
def api_suspend_user(user_id):
    data = _json_or_form()
    reason = _str_field(data, "reason")
    admin.suspend_user(get_db(), user_id, g.user["id"], reason=reason)
    return jsonify(ok=True, suspended=True)


@bp.post("/api/admin/users/<int:user_id>/unsuspend")
@login_required("admin")
def api_unsuspend_user(user_id):
    admin.unsuspend_user(get_db(), user_id)
    return jsonify(ok=True, suspended=False)


@bp.post("/api/admin/venues/<int:venue_id>/toggle")
@login_required("admin")
def api_toggle_venue(venue_id):
    is_active = admin.toggle_venue_active(get_db(), venue_id)
    return jsonify(ok=True, active=is_active)


@bp.post("/api/admin/reviews/<int:review_id>/moderate")
@login_required("admin")
def api_moderate_review(review_id):
    data = _json_or_form()
    action = _str_field(data, "action")
    admin.moderate_review(get_db(), review_id, g.user["id"], action)
    return jsonify(ok=True, action=action.strip().lower())
