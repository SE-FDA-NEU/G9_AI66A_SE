"""Per-hour prices and the per-segment split of a booking (BR12)."""
from datetime import date

from errors import BusinessRuleError

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def hour_prices(conn, venue_id, day):
    """{hour: price} for every opening hour of the venue on that day.

    BR12: each hour is priced on its own. A pricing rule covers the half-open range
    [start_hour, end_hour) on one weekday (0 = Monday, same as date.weekday()); an hour
    no rule covers costs the venue's standard hourly_price.
    """
    if isinstance(day, str):
        day = date.fromisoformat(day)
    venue = conn.execute("SELECT hourly_price, open_hour, close_hour FROM venue WHERE id = ?",
                         (venue_id,)).fetchone()
    rules = conn.execute("SELECT start_hour, end_hour, price_per_hour FROM pricing_rule"
                         " WHERE venue_id = ? AND weekday = ?", (venue_id, day.weekday())).fetchall()
    prices = {}
    for h in range(venue["open_hour"], venue["close_hour"]):
        prices[h] = next((r["price_per_hour"] for r in rules
                          if r["start_hour"] <= h < r["end_hour"]), venue["hourly_price"])
    return prices


def segments(prices, start_hour, hours):
    """Split start_hour .. start_hour + hours into runs of the same hourly price.

    BR12: 19:00-21:00 with peak 17:00-20:00 at 450,000 and standard 300,000 gives two
    segments, 19:00-20:00 = 450,000 and 20:00-21:00 = 300,000. The total is their exact
    sum - nothing is rounded up to the higher price.
    """
    result = []
    for h in range(start_hour, start_hour + hours):
        price = prices[h]
        if result and result[-1]["price_per_hour"] == price:
            seg = result[-1]
            seg["hours"] += 1
            seg["to"] = f"{h + 1:02d}:00"
            seg["price"] += price
        else:
            result.append({"from": f"{h:02d}:00", "to": f"{h + 1:02d}:00", "hours": 1,
                           "price_per_hour": price, "price": price})
    return result


def list_pricing_rules(conn, venue_id):
    """List all pricing rules for a venue ordered by weekday and start hour (BR12)."""
    return conn.execute(
        "SELECT id, venue_id, weekday, start_hour, end_hour, price_per_hour FROM pricing_rule"
        " WHERE venue_id = ? ORDER BY weekday, start_hour", (venue_id,)).fetchall()


def add_pricing_rule(conn, venue_id, weekday, start_hour, end_hour, price_per_hour):
    """Add a new peak pricing rule with overlap prevention (US11, BR12, BR13)."""
    venue = conn.execute("SELECT open_hour, close_hour FROM venue WHERE id = ?", (venue_id,)).fetchone()
    if venue is None:
        raise BusinessRuleError(404, "Venue not found")

    if not 0 <= weekday <= 6:
        raise BusinessRuleError(400, "Please choose a valid weekday (0-6)", "BR12")
    if not (venue["open_hour"] <= start_hour < end_hour <= venue["close_hour"]):
        raise BusinessRuleError(400, f"Time range must be within opening hours ({venue['open_hour']:02d}:00 - {venue['close_hour']:02d}:00)", "BR12")
    if not (1000 <= price_per_hour <= 100_000_000):
        raise BusinessRuleError(400, "Hourly price must be between 1,000 and 100,000,000 VND", "BR13")

    # Overlap check on same weekday (BR12)
    conflict = conn.execute(
        """
        SELECT 1 FROM pricing_rule
        WHERE venue_id = ? AND weekday = ?
          AND NOT (end_hour <= ? OR start_hour >= ?)
        """, (venue_id, weekday, start_hour, end_hour)).fetchone()
    if conflict:
        raise BusinessRuleError(409, "Pricing rules cannot overlap on the same weekday", "BR12")

    cur = conn.execute(
        "INSERT INTO pricing_rule (venue_id, weekday, start_hour, end_hour, price_per_hour)"
        " VALUES (?, ?, ?, ?, ?)", (venue_id, weekday, start_hour, end_hour, price_per_hour))
    conn.commit()
    return cur.lastrowid


def delete_pricing_rule(conn, rule_id, venue_id):
    """Remove a pricing rule (BR12)."""
    conn.execute("DELETE FROM pricing_rule WHERE id = ? AND venue_id = ?", (rule_id, venue_id))
    conn.commit()

