"""Customer reviews and ratings (US12, BR18, BR19)."""
from errors import BusinessRuleError


def submit_review(conn, booking_code, user, rating, comment=""):
    """Customer submits a review for their completed booking (BR18)."""
    booking = conn.execute(
        "SELECT id, customer_id, status FROM booking WHERE code = ?", (booking_code,)).fetchone()
    if booking is None:
        raise BusinessRuleError(404, "Booking not found")
    if booking["customer_id"] != user["id"]:
        raise BusinessRuleError(403, "You do not have permission to review this booking", "BR14")
    if booking["status"] != "completed":
        raise BusinessRuleError(400, "Only completed bookings can be reviewed", "BR18")

    try:
        rating = int(rating)
    except (ValueError, TypeError):
        raise BusinessRuleError(400, "Rating must be between 1 and 5 stars", "BR18")

    if not 1 <= rating <= 5:
        raise BusinessRuleError(400, "Rating must be between 1 and 5 stars", "BR18")

    comment = (comment or "").strip()
    if len(comment) > 1000:
        raise BusinessRuleError(400, "Review comment cannot exceed 1,000 characters", "BR18")

    existing = conn.execute("SELECT 1 FROM review WHERE booking_id = ?", (booking["id"],)).fetchone()
    if existing:
        raise BusinessRuleError(409, "This booking has already been reviewed", "BR18")

    conn.execute(
        "INSERT INTO review (booking_id, rating, comment) VALUES (?, ?, ?)",
        (booking["id"], rating, comment if comment else None))
    conn.commit()


def venue_reviews(conn, venue_id):
    """Visible reviews for a venue (BR19: excludes hidden reviews)."""
    return conn.execute(
        """
        SELECT r.id, r.rating, r.comment, r.created_at, r.report_count,
               u.full_name AS author_name
        FROM review r
        JOIN booking b ON b.id = r.booking_id
        JOIN user u ON u.id = b.customer_id
        WHERE b.venue_id = ? AND r.hidden = 0
        ORDER BY r.created_at DESC
        """, (venue_id,)).fetchall()


def venue_rating_summary(conn, venue_id):
    """Average rating and count of visible reviews."""
    row = conn.execute(
        """
        SELECT AVG(r.rating) AS avg_rating, COUNT(r.id) AS review_count
        FROM review r
        JOIN booking b ON b.id = r.booking_id
        WHERE b.venue_id = ? AND r.hidden = 0
        """, (venue_id,)).fetchone()
    avg = round(row["avg_rating"], 1) if row and row["avg_rating"] else None
    count = row["review_count"] if row else 0
    return {"avg_rating": avg, "review_count": count}


def report_review(conn, review_id):
    """Report a review for abuse; automatically hide after 3 reports (BR19)."""
    rev = conn.execute("SELECT id, report_count FROM review WHERE id = ?", (review_id,)).fetchone()
    if rev is None:
        raise BusinessRuleError(404, "Review not found")

    new_count = rev["report_count"] + 1
    hidden = 1 if new_count >= 3 else 0
    conn.execute(
        "UPDATE review SET report_count = ?, hidden = ? WHERE id = ?",
        (new_count, hidden, review_id))
    conn.commit()
    return {"id": review_id, "report_count": new_count, "hidden": bool(hidden)}
