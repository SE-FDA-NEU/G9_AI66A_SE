"""Sign in and sign out (US02): the /login page and its JSON API."""
from datetime import datetime

from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, session

import auth
from db import get_db
from errors import BusinessRuleError
from guards import start_session

bp = Blueprint("auth", __name__)


def safe_next(target):
    """Only follow ?next= to a page of this site, never to another website."""
    return target if target and target.startswith("/") and not target.startswith("//") else None


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
        user = auth.sign_in(get_db(), email, request.form.get("password", ""), datetime.now())
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


@bp.post("/api/auth/login")
def api_login():
    data = request.get_json(silent=True) or request.form
    user = auth.sign_in(get_db(), data.get("email", ""), data.get("password", ""), datetime.now())
    start_session(user)
    return jsonify(role=user["role"], redirect=auth.LANDING_PAGE[user["role"]])


@bp.post("/api/auth/logout")
def api_logout():
    session.clear()
    return "", 204
