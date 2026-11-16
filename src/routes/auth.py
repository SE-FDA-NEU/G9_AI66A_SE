"""Register and verify the email (US01), sign in and sign out (US02): pages and JSON API."""
import os
from urllib.parse import urlsplit

from flask import (
    Blueprint,
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

import auth
from db import get_db
from errors import BusinessRuleError
from guards import login_required, start_session
from time_utils import vn_now

bp = Blueprint("auth", __name__)


def _now():
    return current_app.config.get("NOW", vn_now)()


def _show_verification_link():
    default = "1" if (current_app.config.get("TESTING") or current_app.debug) else "0"
    return os.environ.get("SHOW_VERIFICATION_LINK", default) == "1"


def _json_or_form_dict():
    if request.is_json:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else None
    if request.form:
        return request.form
    data = request.get_json(silent=True)
    if data is not None and not isinstance(data, dict):
        return None
    return data if isinstance(data, dict) else {}


def safe_next(target):
    """Only follow ?next= to a page of this site, never to another website."""
    if not target or not isinstance(target, str) or "\\" in target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return None
    if not parts.path.startswith("/") or parts.path.startswith("//"):
        return None
    return target


def send_verification_link(email, user_id):
    """Email the verification link (BR4). Sprint 3 has no email server: the link is printed
    in the terminal running the app, and shown on screen while SHOW_VERIFICATION_LINK=1."""
    token = auth.make_verify_token(current_app.config["SECRET_KEY"], user_id, _now())
    link = url_for("auth.verify_page", token=token, _external=True)
    print(f"[email] to {email}: verify your account at {link}", flush=True)
    if _show_verification_link():
        flash(link, "verify-link")


@bp.get("/register")
def register_page():
    return render_template("register.html", form={}, errors={})


@bp.post("/register")
def register_submit():
    form = {k: request.form.get(k, "").strip() for k in ("email", "full_name", "phone")}
    password = request.form.get("password", "")
    conn = get_db()
    problems = auth.check_registration(conn, form["email"], password, form["full_name"], form["phone"])
    if problems:
        # US01 criterion 3: show every message and keep what the user typed
        errors = {p.field: p.message for p in problems}
        return render_template("register.html", form=form, errors=errors), problems[0].status
    user_id = auth.register(conn, form["email"], password, form["full_name"], form["phone"])
    flash(f"Account created. We sent a verification link to {form['email']}.", "success")
    send_verification_link(form["email"], user_id)
    return redirect("/login")


@bp.get("/verify")
def verify_page():
    try:
        auth.verify_email(get_db(), current_app.config["SECRET_KEY"],
                          request.args.get("token", ""), _now())
    except BusinessRuleError as err:
        return render_template("verify.html", error=err.message), err.status
    return render_template("verify.html", error=None)


@bp.post("/verify/resend")
@login_required()
def resend_verification():
    if g.user["email_verified_at"]:
        flash("Your email is already verified.", "info")
    else:
        flash(f"We sent a new verification link to {g.user['email']}.", "success")
        send_verification_link(g.user["email"], g.user["id"])
    return redirect(auth.LANDING_PAGE[g.user["role"]])


@bp.get("/login")
def login_page():
    if g.user:
        return redirect(auth.LANDING_PAGE[g.user["role"]])
    return render_template("login.html", email="", next=request.args.get("next", ""))


@bp.post("/login")
def login_submit():
    email = request.form.get("email", "")
    next_page = request.form.get("next", "")
    try:
        user = auth.sign_in(get_db(), email, request.form.get("password", ""), _now())
    except BusinessRuleError as err:
        return render_template("login.html", email=email, next=next_page, error=err.message), err.status
    start_session(user)
    # BR7: land by role; after an expired session, go back to the page the user was on
    return redirect(safe_next(next_page) or auth.LANDING_PAGE[user["role"]])


@bp.post("/logout")
def logout():
    session.clear()
    flash("You have signed out.", "info")
    return redirect("/search")


@bp.get("/forgot-password")
def forgot_password_page():
    return render_template("forgot_password.html")


@bp.post("/forgot-password")
def forgot_password_submit():
    email = request.form.get("email", "").strip().casefold()
    flash("If an account with that email exists, we sent a password reset link.", "success")
    if email:
        user = get_db().execute(
            "SELECT id, email, password_hash FROM user WHERE lower(email) = ?",
            (email,),
        ).fetchone()
        if user:
            token = auth.make_reset_token(
                current_app.config["SECRET_KEY"],
                user["id"],
                user["password_hash"],
                _now(),
            )
            link = url_for("auth.reset_password_page", token=token, _external=True)
            print(f"[email] to {user['email']}: reset your password at {link}", flush=True)
            if _show_verification_link():
                flash(link, "reset-link")
    return redirect(url_for("auth.forgot_password_page"))


@bp.get("/reset-password")
def reset_password_page():
    token = request.args.get("token", "")
    conn = get_db()
    try:
        user_id = auth.peek_reset_token_user_id(current_app.config["SECRET_KEY"], token)
        user = conn.execute("SELECT id, password_hash FROM user WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise BusinessRuleError(400, "This password reset link is invalid or has expired.")
        auth.verify_reset_token(
            current_app.config["SECRET_KEY"],
            token,
            user["password_hash"],
            _now(),
        )
    except BusinessRuleError as err:
        return render_template("reset_password.html", token=token, error=err.message, invalid=True), err.status
    return render_template("reset_password.html", token=token, error=None, invalid=False)


@bp.post("/reset-password")
def reset_password_submit():
    token = request.form.get("token", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    conn = get_db()
    try:
        user_id = auth.peek_reset_token_user_id(current_app.config["SECRET_KEY"], token)
        user = conn.execute("SELECT id, password_hash FROM user WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise BusinessRuleError(400, "This password reset link is invalid or has expired.")
        auth.verify_reset_token(
            current_app.config["SECRET_KEY"],
            token,
            user["password_hash"],
            _now(),
        )
    except BusinessRuleError as err:
        return render_template("reset_password.html", token=token, error=err.message, invalid=True), err.status

    if new_password != confirm_password:
        return render_template(
            "reset_password.html", token=token, error="Passwords do not match.", invalid=False
        ), 400

    try:
        auth.reset_password(conn, user["id"], new_password)
    except BusinessRuleError as err:
        return render_template("reset_password.html", token=token, error=err.message, invalid=False), err.status

    flash("Your password has been reset. You can now sign in.", "success")
    return redirect(url_for("auth.login_page"))


@bp.get("/account/password")
@login_required()
def change_password_page():
    return render_template("account_password.html", error=None)


@bp.post("/account/password")
@login_required()
def change_password_submit():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    if new_password != confirm_password:
        return render_template("account_password.html", error="New passwords do not match."), 400
    try:
        auth.change_password(get_db(), g.user["id"], current_password, new_password)
    except BusinessRuleError as err:
        return render_template("account_password.html", error=err.message), err.status
    flash("Your password has been updated.", "success")
    return redirect(auth.LANDING_PAGE[g.user["role"]])


@bp.post("/api/auth/register")
def api_register():
    data = _json_or_form_dict()
    if not isinstance(data, dict):
        return jsonify(error="Invalid JSON payload"), 400
    email = data.get("email", "")
    user_id = auth.register(get_db(), email, data.get("password", ""),
                            data.get("full_name", ""), data.get("phone", ""))
    send_verification_link(email.strip() if isinstance(email, str) else "", user_id)
    return jsonify(user_id=user_id), 201


@bp.get("/api/auth/verify")
def api_verify():
    user_id = auth.verify_email(get_db(), current_app.config["SECRET_KEY"],
                                request.args.get("token", ""), _now())
    return jsonify(user_id=user_id, verified=True)


@bp.post("/api/auth/login")
def api_login():
    data = _json_or_form_dict()
    if not isinstance(data, dict):
        return jsonify(error="Invalid JSON payload"), 400
    user = auth.sign_in(get_db(), data.get("email", ""), data.get("password", ""), _now())
    start_session(user)
    return jsonify(role=user["role"], redirect=auth.LANDING_PAGE[user["role"]])


@bp.post("/api/auth/logout")
def api_logout():
    session.clear()
    return "", 204
