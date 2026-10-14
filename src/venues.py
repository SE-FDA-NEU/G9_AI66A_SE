"""Venues: search (US03).

Sport and area come from the fixed lists below, never from typed text (BR9), so
"Cau Giay", "cau giay" and "Q. Cau Giay" can never become three different areas.
"""
from errors import BusinessRuleError

SPORTS = ["Football", "Badminton", "Tennis", "Pickleball"]          # same list as the CHECK in schema.py

# The 12 urban districts of Hanoi (BR9). Adding a district changes this list, not the schema.
AREAS = ["Ba Dinh", "Bac Tu Liem", "Cau Giay", "Dong Da", "Ha Dong", "Hai Ba Trung",
         "Hoan Kiem", "Hoang Mai", "Long Bien", "Nam Tu Liem", "Tay Ho", "Thanh Xuan"]

NO_MATCH = "No venues found"                                         # BR9

# BR9: sport AND area must both match; an empty filter means "any".
# q narrows by name or sport (US03 criterion 3); parameters are bound, never pasted in.
SEARCH_SQL = """
SELECT v.id, v.name, v.sport, v.area, v.address, v.hourly_price, v.open_hour, v.close_hour
FROM venue v
WHERE v.active = 1
  AND (:sport = '' OR v.sport = :sport)
  AND (:area  = '' OR v.area  = :area)
  AND (:q = '' OR v.name LIKE '%' || :q || '%' OR v.sport LIKE '%' || :q || '%')
ORDER BY v.area, v.sport, v.name
"""


def search(conn, sport="", area="", q=""):
    """Return the matching venues. An unknown sport or area is refused, not ignored (BR9)."""
    if sport and sport not in SPORTS:
        raise BusinessRuleError(400, "Please choose a sport from the list", "BR9", "sport")
    if area and area not in AREAS:
        raise BusinessRuleError(400, "Please choose an area from the list", "BR9", "area")
    return conn.execute(SEARCH_SQL, {"sport": sport, "area": area, "q": q.strip()}).fetchall()
