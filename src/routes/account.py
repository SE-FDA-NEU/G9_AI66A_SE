"""The page each role lands on after signing in (BR7): customer and administrator."""
from flask import Blueprint, render_template

from guards import login_required

bp = Blueprint("account", __name__)


@bp.get("/dashboard")
@login_required("customer")
def dashboard():
    return render_template("dashboard.html")


@bp.get("/admin")
@login_required("admin")
def admin():
    return render_template("admin.html")
