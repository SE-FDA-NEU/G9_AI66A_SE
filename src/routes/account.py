"""The page each role lands on after signing in (BR7): customer and administrator."""
from flask import Blueprint, g, render_template

from db import get_db
import booking
from guards import login_required

bp = Blueprint("account", __name__)


@bp.get("/dashboard")
@login_required("customer")
def dashboard():
    upcoming_bookings = booking.upcoming(get_db(), g.user["id"])
    return render_template("dashboard.html", upcoming_bookings=upcoming_bookings)


@bp.get("/admin")
@login_required("admin")
def admin():
    return render_template("admin.html")

