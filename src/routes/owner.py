"""The venue management area, where an owner lands after signing in (BR7)."""
from flask import Blueprint, render_template

from guards import login_required

bp = Blueprint("owner", __name__)


@bp.get("/owner/venues")
@login_required("owner")
def venues():
    return render_template("owner_venues.html")
