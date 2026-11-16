"""The page each role lands on after signing in (BR7): customer."""
from datetime import datetime

from flask import Blueprint, current_app, g, render_template

import booking
from db import get_db
from guards import login_required

bp = Blueprint("account", __name__)


@bp.get("/dashboard")
@login_required("customer")
def dashboard():
    now = current_app.config.get("NOW", datetime.now)()
    upcoming_bookings = booking.upcoming(get_db(), g.user["id"], now=now)
    return render_template("dashboard.html", upcoming_bookings=upcoming_bookings)


