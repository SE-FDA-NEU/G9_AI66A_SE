"""Per-hour prices and the per-segment split of a booking (BR12)."""
from datetime import date


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
