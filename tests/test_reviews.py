"""Tests for US12 (US25: Customer leaves a review and rating).
Business Rules: BR18, BR19.
"""
from db import connect
import reviews


def test_submit_review_for_completed_booking(client, login, db):
    # US12, BR18: Trang submits a review for her completed booking BK-000102
    login("trang@example.com")
    res = client.post("/my-bookings/BK-000102/review", data={
        "rating": 5,
        "comment": "Sân đẹp, cỏ mới, đèn sáng!"
    }, follow_redirects=True)
    assert res.status_code == 200
    page = res.get_data(as_text=True)
    assert "Thank you for submitting your review!" in page

    # Verify review appears on venue 2 page
    venue_page = client.get("/venues/2").get_data(as_text=True)
    assert "Sân đẹp, cỏ mới, đèn sáng!" in venue_page
    assert "Do Thu Trang" in venue_page


def test_cannot_review_uncompleted_booking(client, login, db):
    # BR18: Only a completed booking can be reviewed
    login("minh@example.com")
    # BK-000103 is confirmed, not completed
    res = client.post("/my-bookings/BK-000103/review", data={
        "rating": 4,
        "comment": "Tốt"
    }, follow_redirects=True)
    page = res.get_data(as_text=True)
    assert "Only completed bookings can be reviewed" in page


def test_cannot_review_another_users_booking(client, login, db):
    # BR14: Cannot review another user's booking
    login("trang@example.com")
    res = client.post("/my-bookings/BK-000101/review", data={
        "rating": 5,
        "comment": "Tốt"
    }, follow_redirects=True)
    page = res.get_data(as_text=True)
    assert "You do not have permission to review this booking" in page


def test_report_review_hides_automatically_after_3_reports(client, db):
    # BR19: A review with 3 valid abuse reports is hidden automatically
    with connect(db) as conn:
        rev_id = conn.execute("SELECT id FROM review LIMIT 1").fetchone()[0]

    # Report 1
    client.post(f"/venues/1/reviews/{rev_id}/report")
    with connect(db) as conn:
        assert conn.execute("SELECT report_count, hidden FROM review WHERE id = ?", (rev_id,)).fetchone()["report_count"] == 1

    # Report 2
    client.post(f"/venues/1/reviews/{rev_id}/report")

    # Report 3 -> automatically hidden!
    client.post(f"/venues/1/reviews/{rev_id}/report")
    with connect(db) as conn:
        row = conn.execute("SELECT report_count, hidden FROM review WHERE id = ?", (rev_id,)).fetchone()
        assert row["report_count"] == 3
        assert row["hidden"] == 1
