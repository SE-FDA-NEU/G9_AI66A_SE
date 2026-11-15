"""Register and verify the email (US01), sign in and sign out (US02): pages and JSON API."""
import os
from datetime import datetime

from flask import (Blueprint, current_app, flash, g, jsonify, redirect, render_template, request,
                   session, url_for)

import auth
from db import get_db
from errors import BusinessRuleError
from guards import login_required, start_session

bp = Blueprint("auth", __name__)


def safe_next(target):
    """Only follow ?next= to a page of this site, never to another website."""
    return target if target and target.startswith("/") and not target.startswith("//") else None


def send_verification_link(email, user_id):
    """Email the verification link (BR4). Sprint 3 has no email server: the link is printed
    in the terminal running the app, and shown on screen while SHOW_VERIFICATION_LINK=1."""
    token = auth.make_verify_token(current_app.config["SECRET_KEY"], user_id, datetime.now())
    link = url_for("auth.verify_page", token=token, _external=True)
    print(f"[email] to {email}: verify your account at {link}", flush=True)
    if os.environ.get("SHOW_VERIFICATION_LINK", "1") == "1":
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
                          request.args.get("token", ""), datetime.now())
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
    now = current_app.config.get("NOW", datetime.now)()
    try:
        user = auth.sign_in(get_db(), email, request.form.get("password", ""), now)
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


def _str_field(data, key):
    val = data.get(key, "")
    if val is None:
        return ""
    if not isinstance(val, str):
        raise BusinessRuleError(400, f"Invalid field '{key}': expected text")
    return val


@bp.post("/api/auth/register")
def api_register():
    data = request.get_json(silent=True) or request.form
    email = _str_field(data, "email")
    password = _str_field(data, "password")
    full_name = _str_field(data, "full_name")
    phone = _str_field(data, "phone")
    user_id = auth.register(get_db(), email, password, full_name, phone)
    send_verification_link(email.strip(), user_id)
    return jsonify(user_id=user_id), 201


@bp.get("/api/auth/verify")
def api_verify():
    now = current_app.config.get("NOW", datetime.now)()
    user_id = auth.verify_email(get_db(), current_app.config["SECRET_KEY"],
                                request.args.get("token", ""), now)
    return jsonify(user_id=user_id, verified=True)


@bp.post("/api/auth/login")
def api_login():
    data = request.get_json(silent=True) or request.form
    now = current_app.config.get("NOW", datetime.now)()
    email = _str_field(data, "email")
    password = _str_field(data, "password")
    user = auth.sign_in(get_db(), email, password, now)
    start_session(user)
    return jsonify(role=user["role"], redirect=auth.LANDING_PAGE[user["role"]])


@bp.post("/api/auth/logout")
def api_logout():
    session.clear()
    return "", 204
