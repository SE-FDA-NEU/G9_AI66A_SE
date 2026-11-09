"""Time and timezone utilities.

All venue bookings, opening hours, and schedules operate in Vietnam time (UTC+7).
This module ensures consistency across local machines and cloud runtimes (e.g. Vercel)
that run in UTC.
"""
from datetime import datetime, timezone, timedelta

# Vietnam Standard Time (UTC+7, permanent, no DST)
VN_TZ = timezone(timedelta(hours=7))


def vn_now() -> datetime:
    """Return naive datetime in Vietnam local time (UTC+7)."""
    return datetime.now(VN_TZ).replace(tzinfo=None)
