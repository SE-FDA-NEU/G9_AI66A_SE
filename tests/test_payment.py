"""Unit and integration tests for Simulated Online QR Payment & Auto-Refund."""
from datetime import datetime, timedelta

import pytest

import booking as booking_svc
import payment
from app import create_app
from db import connect
from errors import BusinessRuleError

NOW = datetime(2026, 10, 11, 9, 0)
TUESDAY = "2026-10-13"


def _user(conn, email):
    return conn.execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()


@pytest.fixture
def app(db):
    app = create_app(database=db)
    app.config["TESTING"] = True
    app.config["NOW"] = lambda: NOW
    return app


def _signed_in(app, email):
    client = app.test_client()
    with connect(app.config["DATABASE"]) as conn:
        uid = _user(conn, email)["id"]
    with client.session_transaction() as s:
        s["user_id"] = uid
    return client


def test_generate_qr_svg_is_deterministic_and_valid():
    svg1 = payment.generate_qr_svg("http://localhost:5000/payment/PAY-1234ABCD/scan")
    svg2 = payment.generate_qr_svg("http://localhost:5000/payment/PAY-1234ABCD/scan")
    svg3 = payment.generate_qr_svg("http://localhost:5000/payment/PAY-9999EFGH/scan")
    assert svg1 == svg2
    assert svg1 != svg3
    assert svg1.startswith("<svg ")
    assert svg1.endswith("</svg>")
    assert 'viewBox="0 0 29 29"' in svg1


def test_payment_lifecycle_and_auto_refund(db):
    with connect(db) as conn:
        cust = _user(conn, "minh@example.com")
        other = _user(conn, "trang@example.com")

        # Venue 1 on Tuesday 16:00-18:00: 16:00 (300k) + 17:00 peak (450k) = 750,000 VND
        sess = payment.create_session(conn, cust, 1, TUESDAY, 16, 2, NOW)
        assert sess["token"].startswith("PAY-")
        assert len(sess["otp_code"]) == 6
        assert sess["amount"] == 750000
        assert sess["status"] == "pending"
        assert sess["venue_name"]

        # Ownership check (BR14)
        with pytest.raises(BusinessRuleError) as exc:
            payment.get_session(conn, sess["token"], other)
        assert exc.value.status == 403

        # Missing session -> 404
        with pytest.raises(BusinessRuleError) as exc:
            payment.get_session(conn, "PAY-MISSING")
        assert exc.value.status == 404

        # Cannot confirm before QR accepted
        with pytest.raises(BusinessRuleError) as exc:
            payment.confirm_and_book(conn, sess["token"], cust, sess["otp_code"], NOW)
        assert exc.value.status == 400

        # Invalid / mismatched amount rejected
        with pytest.raises(BusinessRuleError) as exc:
            payment.accept_qr_payment(conn, sess["token"], "abc")
        assert exc.value.status == 400

        with pytest.raises(BusinessRuleError) as exc:
            payment.accept_qr_payment(conn, sess["token"], "500000")
        assert exc.value.status == 400
        assert "750,000 VND" in exc.value.message

        # Exact amount accepted (formatted with commas)
        accepted = payment.accept_qr_payment(conn, sess["token"], "750,000")
        assert accepted["status"] == "accepted"
        assert accepted["paid_amount"] == 750000

        # Wrong OTP rejected
        with pytest.raises(BusinessRuleError) as exc:
            payment.confirm_and_book(conn, sess["token"], cust, "000000", NOW)
        assert exc.value.status == 400

        # Correct OTP creates booking and marks paid
        result = payment.confirm_and_book(conn, sess["token"], cust, sess["otp_code"], NOW)
        code = result["code"]
        assert code.startswith("BK-")

        # Idempotent re-confirm returns booking code
        again = payment.confirm_and_book(conn, sess["token"], cust, sess["otp_code"], NOW)
        assert again == {"code": code}

        # Cannot re-accept already paid session
        with pytest.raises(BusinessRuleError) as exc:
            payment.accept_qr_payment(conn, sess["token"], "750000")
        assert exc.value.status == 400

        # find_for_customer and list_for_customer include payment fields
        bk, _segs = booking_svc.find_for_customer(conn, code, cust)
        assert bk["payment_status"] == "paid"
        assert bk["paid_amount"] == 750000
        assert bk["refunded_amount"] == 0
        assert bk["payment_token"] == sess["token"]

        rows = booking_svc.list_for_customer(conn, cust["id"], now=NOW)
        matched = [r for r in rows if r["code"] == code][0]
        assert matched["payment_status"] == "paid"
        assert matched["paid_amount"] == 750000

        # Cancel >= 24h before -> 100% auto-refund
        cancel_res = booking_svc.cancel_booking(conn, code, cust, NOW)
        assert cancel_res["refund_amount"] == 750000
        ps = payment.get_for_booking(conn, code)
        assert ps["status"] == "refunded"
        assert ps["refunded_amount"] == 750000
        assert ps["refunded_at"] is not None


def test_partial_auto_refund_between_2h_and_24h(db):
    with connect(db) as conn:
        cust = _user(conn, "minh@example.com")
        sess = payment.create_session(conn, cust, 1, TUESDAY, 10, 1, NOW)
        payment.accept_qr_payment(conn, sess["token"], str(sess["amount"]))
        res = payment.confirm_and_book(conn, sess["token"], cust, sess["otp_code"], NOW)

        # Cancel 5 hours before 2026-10-13 10:00 -> 50% refund -> partially_refunded
        cancel_time = datetime(2026, 10, 13, 5, 0)
        cancel_res = booking_svc.cancel_booking(conn, res["code"], cust, cancel_time)
        assert cancel_res["refund_percent"] == 50
        ps = payment.get_for_booking(conn, res["code"])
        assert ps["status"] == "partially_refunded"
        assert ps["refunded_amount"] == sess["amount"] // 2


def test_checkout_and_status_api_routes(app):
    # Unauthenticated checkout redirects to login
    anon = app.test_client()
    r = anon.post("/booking/1/checkout", data={"date": TUESDAY, "start_hour": "10", "hours": "1"})
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]

    # Unauthenticated status API -> 401
    r = anon.get("/api/payment/PAY-ANYTHING/status")
    assert r.status_code == 401

    client = _signed_in(app, "minh@example.com")
    r = client.post("/booking/1/checkout", data={"date": TUESDAY, "start_hour": "10", "hours": "1"})
    assert r.status_code == 302
    location = r.headers["Location"]
    assert "/payment/PAY-" in location
    token = location.rsplit("/", 1)[-1]

    status_resp = client.get(f"/api/payment/{token}/status")
    assert status_resp.status_code == 200
    data = status_resp.get_json()
    assert data == {"status": "pending", "paid_amount": 0, "booking_code": None}

    # Another user gets 403
    other = _signed_in(app, "trang@example.com")
    assert other.get(f"/api/payment/{token}/status").status_code == 403
