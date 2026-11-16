"""Comprehensive test & stress-test suite for the Admin Portal (BR1-BR3, BR6-BR7, BR14, BR19)."""
import ast
from datetime import datetime
from pathlib import Path

import admin
import auth
from db import connect
from db_compat import CompatCursor
from errors import BusinessRuleError
import reviews


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_id(db_path, email):
    with connect(db_path) as conn:
        row = conn.execute("SELECT id FROM user WHERE lower(email) = ?", (email.casefold(),)).fetchone()
        return row["id"]


def _get_user(db_path, email):
    with connect(db_path) as conn:
        return conn.execute("SELECT * FROM user WHERE lower(email) = ?", (email.casefold(),)).fetchone()


def _get_venue(db_path, venue_id=1):
    with connect(db_path) as conn:
        return conn.execute("SELECT * FROM venue WHERE id = ?", (venue_id,)).fetchone()


def _get_review_by_booking_code(db_path, code):
    with connect(db_path) as conn:
        return conn.execute(
            """
            SELECT r.*, b.venue_id
            FROM review r
            JOIN booking b ON b.id = r.booking_id
            WHERE b.code = ?
            """,
            (code,),
        ).fetchone()


# ---------------------------------------------------------------------------
# 1. Access control (BR7, BR14)
# ---------------------------------------------------------------------------

def test_unauthenticated_access_control(client):
    # HTML routes redirect to /login
    for path in ("/admin", "/admin?tab=venues", "/admin?tab=accounts", "/admin?tab=moderation"):
        resp = client.get(path)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    for path in (
        "/admin/users/create",
        "/admin/users/1/suspend",
        "/admin/users/1/unsuspend",
        "/admin/venues/1/toggle",
        "/admin/reviews/1/moderate",
    ):
        resp = client.post(path)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    # API routes return 401
    assert client.get("/api/admin/stats").status_code == 401
    for path in (
        "/api/admin/users",
        "/api/admin/users/1/suspend",
        "/api/admin/users/1/unsuspend",
        "/api/admin/venues/1/toggle",
        "/api/admin/reviews/1/moderate",
    ):
        assert client.post(path).status_code == 401


def test_non_admin_forbidden_on_admin_routes(client, login):
    for email in ("minh@example.com", "lan.owner@example.com"):
        login(email)
        assert client.get("/admin").status_code == 403
        assert client.get("/api/admin/stats").status_code == 403
        assert client.post("/admin/users/create", data={"email": "x@example.com"}).status_code == 403
        assert client.post("/api/admin/users", json={"email": "x@example.com"}).status_code == 403
        assert client.post("/admin/users/1/suspend").status_code == 403
        assert client.post("/api/admin/users/1/suspend").status_code == 403
        assert client.post("/admin/venues/1/toggle").status_code == 403
        assert client.post("/api/admin/venues/1/toggle").status_code == 403
        assert client.post("/admin/reviews/1/moderate", data={"action": "approve"}).status_code == 403
        assert client.post("/api/admin/reviews/1/moderate", json={"action": "approve"}).status_code == 403


def test_admin_login_and_all_four_tabs(client, login):
    login_resp = login("admin@example.com")
    assert login_resp.status_code == 302
    assert login_resp.headers["Location"].endswith("/admin")

    for tab in ("overview", "venues", "accounts", "moderation"):
        resp = client.get(f"/admin?tab={tab}")
        assert resp.status_code == 200
        assert b"Administration" in resp.data


# ---------------------------------------------------------------------------
# 2. Platform analytics & per-venue stats
# ---------------------------------------------------------------------------

def test_platform_analytics_kpis_and_math_accuracy(client, db, login):
    login("admin@example.com")
    resp = client.get("/api/admin/stats")
    assert resp.status_code == 200
    payload = resp.get_json()
    stats = payload["stats"]

    with connect(db) as conn:
        expected_users = conn.execute("SELECT COUNT(*) AS c FROM user").fetchone()["c"]
        expected_bookings = conn.execute("SELECT COUNT(*) AS c FROM booking").fetchone()["c"]
        expected_cancelled = conn.execute(
            "SELECT COUNT(*) AS c FROM booking WHERE status = 'cancelled'"
        ).fetchone()["c"]
        rev_row = conn.execute(
            """
            SELECT COALESCE(SUM(total_price), 0) AS gross,
                   COALESCE(SUM(COALESCE(refund_amount, 0)), 0) AS refunded,
                   COALESCE(SUM(total_price - COALESCE(refund_amount, 0)), 0) AS net
            FROM booking
            """
        ).fetchone()

    assert stats["total_users"] == expected_users == 8
    assert stats["customers_count"] == 4
    assert stats["owners_count"] == 3
    assert stats["admins_count"] == 1
    assert stats["suspended_users_count"] == 0
    assert stats["unverified_users_count"] == 1

    assert stats["total_bookings"] == expected_bookings == 10
    assert stats["confirmed_bookings"] == 4
    assert stats["completed_bookings"] == 4
    assert stats["cancelled_bookings"] == expected_cancelled == 2
    assert stats["cancellation_rate"] == 20.0

    # Verify accounting identity: gross_revenue - total_refunded == net_revenue
    assert stats["gross_revenue"] == rev_row["gross"]
    assert stats["total_refunded"] == rev_row["refunded"] == 625000
    assert stats["net_revenue"] == rev_row["net"]
    assert stats["gross_revenue"] - stats["total_refunded"] == stats["net_revenue"]

    # Sport breakdown covers all 4 sports and shares sum to ~100%
    sport_breakdown = payload["sport_breakdown"]
    assert [row["sport"] for row in sport_breakdown] == ["Football", "Badminton", "Tennis", "Pickleball"]
    assert sum(row["booking_count"] for row in sport_breakdown) == expected_bookings
    assert sum(row["net_revenue"] for row in sport_breakdown) == stats["net_revenue"]
    assert round(sum(row["revenue_share_pct"] for row in sport_breakdown), 0) == 100

    # Area breakdown sums match total venues and bookings
    area_breakdown = payload["area_breakdown"]
    assert len(area_breakdown) > 0
    assert sum(row["venue_count"] for row in area_breakdown) == stats["total_venues"]
    assert sum(row["booking_count"] for row in area_breakdown) == expected_bookings
    assert sum(row["net_revenue"] for row in area_breakdown) == stats["net_revenue"]


def test_venue_analytics_filters_and_tab_rendering(client, db, login):
    with connect(db) as conn:
        football = admin.get_venue_analytics(conn, sport="Football")
        assert len(football) > 0
        assert all(v["sport"] == "Football" for v in football)

        cau_giay = admin.get_venue_analytics(conn, area="Cau Giay")
        assert len(cau_giay) > 0
        assert all(v["area"] == "Cau Giay" for v in cau_giay)

        search_tn = admin.get_venue_analytics(conn, q="Thong Nhat")
        assert len(search_tn) == 1
        assert search_tn[0]["name"] == "Thong Nhat Football Pitch"
        assert search_tn[0]["total_bookings"] >= 3

        # Search by owner name
        search_owner = admin.get_venue_analytics(conn, q="Nguyen Thi Lan")
        assert len(search_owner) > 0
        assert all(v["owner_name"] == "Nguyen Thi Lan" for v in search_owner)

    login("admin@example.com")
    resp = client.get("/admin?tab=venues&sport=Football&q=Thong+Nhat")
    assert resp.status_code == 200
    assert b"Thong Nhat Football Pitch" in resp.data


# ---------------------------------------------------------------------------
# 3. Account creation (POST /admin/users/create & POST /api/admin/users)
# ---------------------------------------------------------------------------

def test_admin_creates_owner_auto_verified_and_can_sign_in(client, db, login):
    login("admin@example.com")
    resp = client.post(
        "/admin/users/create",
        data={
            "email": "new.owner@example.com",
            "password": "Password1",
            "full_name": "New Venue Owner",
            "phone": "0912340001",
            "role": "owner",
            "auto_verify": "1",
        },
    )
    assert resp.status_code == 302
    assert "/admin?tab=accounts" in resp.headers["Location"]

    created = _get_user(db, "new.owner@example.com")
    assert created is not None
    assert created["role"] == "owner"
    assert created["email_verified_at"] is not None

    # Unchecked auto_verify creates an unverified user
    resp_unverified = client.post(
        "/admin/users/create",
        data={
            "email": "unverified.cust@example.com",
            "password": "Password1",
            "full_name": "Unverified Customer",
            "phone": "0912340099",
            "role": "customer",
        },
    )
    assert resp_unverified.status_code == 302
    unverified_user = _get_user(db, "unverified.cust@example.com")
    assert unverified_user is not None
    assert unverified_user["email_verified_at"] is None

    # Owner signs in and lands on /owner/venues (BR7)
    client.post("/logout")
    signin_resp = login("new.owner@example.com", "Password1")
    assert signin_resp.status_code == 302
    assert signin_resp.headers["Location"].endswith("/owner/venues")


def test_admin_create_user_rejects_duplicate_phone(client, login):
    login("admin@example.com")
    resp = client.post(
        "/api/admin/users",
        json={
            "email": "dup.phone@example.com",
            "password": "Password1",
            "full_name": "Duplicate Phone",
            "phone": "0901234567",  # Minh's seeded phone
            "role": "customer",
        },
    )
    assert resp.status_code == 409
    assert "This phone number is already in use" in resp.get_json()["error"]


def test_admin_creates_customer_and_admin_via_api(client, db, login):
    login("admin@example.com")

    cust_resp = client.post(
        "/api/admin/users",
        json={
            "email": "new.cust@example.com",
            "password": "Password1",
            "full_name": "New Customer",
            "phone": "0912340002",
            "role": "customer",
        },
    )
    assert cust_resp.status_code == 201
    assert cust_resp.get_json()["role"] == "customer"

    adm_resp = client.post(
        "/api/admin/users",
        json={
            "email": "new.admin@example.com",
            "password": "Password1",
            "full_name": "Second Admin",
            "phone": "0912340003",
            "role": "admin",
        },
    )
    assert adm_resp.status_code == 201
    assert adm_resp.get_json()["role"] == "admin"

    assert _get_user(db, "new.cust@example.com")["role"] == "customer"
    assert _get_user(db, "new.admin@example.com")["role"] == "admin"


def test_admin_create_user_validation_rules(client, login):
    login("admin@example.com")

    # Invalid role -> 400 (BR7)
    bad_role = client.post(
        "/api/admin/users",
        json={
            "email": "badrole@example.com",
            "password": "Password1",
            "full_name": "Bad Role",
            "phone": "0912340004",
            "role": "superadmin",
        },
    )
    assert bad_role.status_code == 400
    assert bad_role.get_json()["rule"] == "BR7"

    # Duplicate email -> 409 (BR1)
    dup_email = client.post(
        "/api/admin/users",
        json={
            "email": "MINH@example.com",
            "password": "Password1",
            "full_name": "Duplicate User",
            "phone": "0912340005",
            "role": "customer",
        },
    )
    assert dup_email.status_code == 409
    assert dup_email.get_json()["rule"] == "BR1"

    # Weak password -> 400 (BR2)
    for weak_pw in ("short1", "onlyletters", "12345678"):
        weak_resp = client.post(
            "/api/admin/users",
            json={
                "email": f"weak_{weak_pw}@example.com",
                "password": weak_pw,
                "full_name": "Weak Pass",
                "phone": "0912340006",
                "role": "customer",
            },
        )
        assert weak_resp.status_code == 400
        assert weak_resp.get_json()["rule"] == "BR2"

    # Invalid phone -> 400 (BR3)
    for bad_phone in ("09123", "1912345678", "091234567a"):
        phone_resp = client.post(
            "/api/admin/users",
            json={
                "email": f"phone_{bad_phone}@example.com",
                "password": "Password1",
                "full_name": "Bad Phone",
                "phone": bad_phone,
                "role": "customer",
            },
        )
        assert phone_resp.status_code == 400
        assert phone_resp.get_json()["rule"] == "BR3"


# ---------------------------------------------------------------------------
# 4. Account suspension & enforcement
# ---------------------------------------------------------------------------

def test_suspend_blocks_sign_in_only_with_right_password(client, db, login):
    minh_id = _get_user_id(db, "minh@example.com")

    login("admin@example.com")
    resp = client.post(f"/api/admin/users/{minh_id}/suspend", json={"reason": "No-show abuse"})
    assert resp.status_code == 200
    assert resp.get_json()["suspended"] is True

    client.post("/logout")

    # Wrong password still returns 401 BR6 (must not leak suspension status)
    wrong_pw_resp = login("minh@example.com", "wrongpass1")
    assert wrong_pw_resp.status_code == 401
    with connect(db) as conn:
        try:
            auth.sign_in(conn, "minh@example.com", "wrongpass1", datetime.now())
            assert False, "Expected BusinessRuleError"
        except BusinessRuleError as err:
            assert err.status == 401
            assert err.rule == "BR6"

    # Right password returns 403 BR14
    right_pw_resp = login("minh@example.com", "sanbong1")
    assert right_pw_resp.status_code == 403
    assert b"suspended" in right_pw_resp.data.lower()
    with connect(db) as conn:
        try:
            auth.sign_in(conn, "minh@example.com", "sanbong1", datetime.now())
            assert False, "Expected BusinessRuleError"
        except BusinessRuleError as err:
            assert err.status == 403
            assert err.rule == "BR14"


def test_active_session_invalidated_immediately_upon_suspension(db):
    from app import create_app

    app = create_app(database=db)
    app.config["TESTING"] = True
    admin_client = app.test_client()
    user_client = app.test_client()
    owner_client = app.test_client()

    # Customer and owner log in and have active sessions
    assert user_client.post("/login", data={"email": "trang@example.com", "password": "sanbong1"}).status_code == 302
    assert user_client.get("/dashboard").status_code == 200
    assert owner_client.post("/login", data={"email": "hung.owner@example.com", "password": "sanbong1"}).status_code == 302
    assert owner_client.get("/api/owner/venues").status_code == 200

    # Admin suspends both
    assert admin_client.post("/login", data={"email": "admin@example.com", "password": "sanbong1"}).status_code == 302
    trang_id = _get_user_id(db, "trang@example.com")
    hung_id = _get_user_id(db, "hung.owner@example.com")
    assert admin_client.post(f"/api/admin/users/{trang_id}/suspend", json={"reason": "Chargeback"}).status_code == 200
    assert admin_client.post(f"/api/admin/users/{hung_id}/suspend", json={"reason": "Policy"}).status_code == 200

    # Customer's very next HTML request is immediately rejected / redirected to /login
    next_html = user_client.get("/dashboard")
    assert next_html.status_code == 302
    assert "/login" in next_html.headers["Location"]

    # Owner's very next API request is immediately rejected with 403 (BR14), and subsequent request is 401 (session cleared)
    next_api = owner_client.get("/api/owner/venues")
    assert next_api.status_code == 403
    assert next_api.get_json()["rule"] == "BR14"
    assert owner_client.get("/api/owner/venues").status_code == 401


def test_self_suspension_guard_and_unsuspend_restores_access(client, db, login):
    admin_id = _get_user_id(db, "admin@example.com")
    owner_id = _get_user_id(db, "lan.owner@example.com")

    login("admin@example.com")

    # Self-suspension guard -> 400
    self_resp = client.post(f"/api/admin/users/{admin_id}/suspend", json={"reason": "Test"})
    assert self_resp.status_code == 400
    assert self_resp.get_json()["rule"] == "BR14"
    assert _get_user(db, "admin@example.com")["suspended"] == 0

    # Suspend owner, then unsuspend via HTML route
    assert client.post(f"/admin/users/{owner_id}/suspend", data={"reason": "Audit"}).status_code == 302
    assert _get_user(db, "lan.owner@example.com")["suspended"] == 1

    assert client.post(f"/admin/users/{owner_id}/unsuspend").status_code == 302
    assert _get_user(db, "lan.owner@example.com")["suspended"] == 0

    # Owner can sign in again
    client.post("/logout")
    signin_resp = login("lan.owner@example.com", "sanbong1")
    assert signin_resp.status_code == 302
    assert signin_resp.headers["Location"].endswith("/owner/venues")


# ---------------------------------------------------------------------------
# 5. Venue toggle
# ---------------------------------------------------------------------------

def test_venue_toggle_and_404(client, db, login):
    login("admin@example.com")
    initial_active = bool(_get_venue(db, 1)["active"])
    assert initial_active is True

    # Toggle 1 -> 0 via API
    r1 = client.post("/api/admin/venues/1/toggle")
    assert r1.status_code == 200
    assert r1.get_json() == {"ok": True, "active": False}
    assert _get_venue(db, 1)["active"] == 0

    # Toggle 0 -> 1 via HTML route
    r2 = client.post("/admin/venues/1/toggle")
    assert r2.status_code == 302
    assert "/admin?tab=venues" in r2.headers["Location"]
    assert _get_venue(db, 1)["active"] == 1

    # 404 on nonexistent venue
    r404 = client.post("/api/admin/venues/999999/toggle")
    assert r404.status_code == 404


# ---------------------------------------------------------------------------
# 6. Review moderation queue (BR19)
# ---------------------------------------------------------------------------

def test_review_moderation_report_3x_approve_reject_and_invalid_action(client, db, login):
    # BK-000101 is seeded with report_count=0, hidden=0, moderation_status='active'
    rev = _get_review_by_booking_code(db, "BK-000101")
    review_id = rev["id"]
    venue_id = rev["venue_id"]
    comment_bytes = rev["comment"].encode("utf-8")

    # Visible initially on venue page
    assert comment_bytes in client.get(f"/venues/{venue_id}").data

    # Report twice -> still visible
    for expected_count in (1, 2):
        rep = client.post(f"/venues/{venue_id}/reviews/{review_id}/report")
        assert rep.status_code == 302
        updated = _get_review_by_booking_code(db, "BK-000101")
        assert updated["report_count"] == expected_count
        assert updated["hidden"] == 0

    # 3rd report -> hidden=1, moderation_status='pending', hidden from venue page
    rep3 = client.post(f"/venues/{venue_id}/reviews/{review_id}/report")
    assert rep3.status_code == 302
    flagged = _get_review_by_booking_code(db, "BK-000101")
    assert flagged["report_count"] == 3
    assert flagged["hidden"] == 1
    assert flagged["moderation_status"] == "pending"
    assert comment_bytes not in client.get(f"/venues/{venue_id}").data

    # Appears in admin moderation queue
    with connect(db) as conn:
        pending_ids = [r["id"] for r in admin.list_moderation_reviews(conn, mod_status="pending")]
        assert review_id in pending_ids

    login("admin@example.com")
    mod_page = client.get("/admin?tab=moderation")
    assert mod_page.status_code == 200
    assert comment_bytes in mod_page.data

    # Invalid moderation action -> 400
    bad_action = client.post(f"/api/admin/reviews/{review_id}/moderate", json={"action": "delete"})
    assert bad_action.status_code == 400

    # Approve -> hidden=0, report_count=0, moderation_status='approved', visible again on venue page
    app_resp = client.post(f"/admin/reviews/{review_id}/moderate", data={"action": "approve"})
    assert app_resp.status_code == 302
    assert "/admin?tab=moderation" in app_resp.headers["Location"]

    approved = _get_review_by_booking_code(db, "BK-000101")
    assert approved["hidden"] == 0
    assert approved["report_count"] == 0
    assert approved["moderation_status"] == "approved"
    assert comment_bytes in client.get(f"/venues/{venue_id}").data

    # Reject on BK-000107 (already seeded as pending/hidden=1) -> stays hidden=1, moderation_status='rejected'
    rev2 = _get_review_by_booking_code(db, "BK-000107")
    rej_resp = client.post(f"/api/admin/reviews/{rev2['id']}/moderate", json={"action": "reject"})
    assert rej_resp.status_code == 200
    assert rej_resp.get_json() == {"ok": True, "action": "reject"}

    rejected = _get_review_by_booking_code(db, "BK-000107")
    assert rejected["hidden"] == 1
    assert rejected["moderation_status"] == "rejected"
    assert rejected["comment"].encode("utf-8") not in client.get(f"/venues/{rev2['venue_id']}").data


def test_admin_dashboard_filters_and_stats_rendering(client, login):
    login("admin@example.com")

    overview = client.get("/admin?tab=overview")
    assert overview.status_code == 200
    assert b"Gross Revenue" in overview.data or b"Net Revenue" in overview.data

    accounts = client.get("/admin?tab=accounts&role=owner&status=active&q=Lan")
    assert accounts.status_code == 200
    assert b"lan.owner@example.com" in accounts.data
    assert b"minh@example.com" not in accounts.data

    moderation = client.get("/admin?tab=moderation&mod_status=pending")
    assert moderation.status_code == 200
    assert b"Court surface was wet" in moderation.data


def test_admin_creates_user_with_auto_verify_true_and_false(client, db, login):
    login("admin@example.com")

    # HTML form: auto_verify = "1"
    r1 = client.post(
        "/admin/users/create",
        data={
            "email": "html.verified@example.com",
            "password": "Password1",
            "full_name": "HTML Verified",
            "phone": "0912340011",
            "role": "customer",
            "auto_verify": "1",
        },
    )
    assert r1.status_code == 302
    assert _get_user(db, "html.verified@example.com")["email_verified_at"] is not None

    # HTML form: auto_verify = "0"
    r2 = client.post(
        "/admin/users/create",
        data={
            "email": "html.unverified@example.com",
            "password": "Password1",
            "full_name": "HTML Unverified",
            "phone": "0912340012",
            "role": "customer",
            "auto_verify": "0",
        },
    )
    assert r2.status_code == 302
    assert _get_user(db, "html.unverified@example.com")["email_verified_at"] is None

    # JSON API: auto_verify = True and False
    r3 = client.post(
        "/api/admin/users",
        json={
            "email": "api.verified@example.com",
            "password": "Password1",
            "full_name": "API Verified",
            "phone": "0912340013",
            "role": "owner",
            "auto_verify": True,
        },
    )
    assert r3.status_code == 201
    assert _get_user(db, "api.verified@example.com")["email_verified_at"] is not None

    r4 = client.post(
        "/api/admin/users",
        json={
            "email": "api.unverified@example.com",
            "password": "Password1",
            "full_name": "API Unverified",
            "phone": "0912340014",
            "role": "owner",
            "auto_verify": False,
        },
    )
    assert r4.status_code == 201
    assert _get_user(db, "api.unverified@example.com")["email_verified_at"] is None


def test_api_admin_and_bookings_handle_invalid_json_and_suspended_cleanly(db):
    from app import create_app

    app = create_app(database=db)
    app.config["TESTING"] = True
    admin_client = app.test_client()
    cust_client = app.test_client()

    assert admin_client.post("/login", data={"email": "admin@example.com", "password": "sanbong1"}).status_code == 302
    assert cust_client.post("/login", data={"email": "minh@example.com", "password": "sanbong1"}).status_code == 302

    # Malformed JSON & non-dict JSON on /api/admin/* -> 400 (never 500)
    for endpoint in (
        "/api/admin/users",
        "/api/admin/users/4/suspend",
        "/api/admin/reviews/1/moderate",
    ):
        malformed = admin_client.post(endpoint, data="{bad json", content_type="application/json")
        assert malformed.status_code == 400
        non_dict = admin_client.post(endpoint, json=["not", "a", "dict"])
        assert non_dict.status_code == 400

    # Malformed JSON & non-dict JSON on /api/bookings -> 400 (never 500)
    b_malformed = cust_client.post("/api/bookings", data="{bad json", content_type="application/json")
    assert b_malformed.status_code == 400
    b_non_dict = cust_client.post("/api/bookings", json=["not", "a", "dict"])
    assert b_non_dict.status_code == 400

    # Suspend customer while active session exists, then hit /api/bookings*
    minh_id = _get_user_id(db, "minh@example.com")
    assert admin_client.post(f"/api/admin/users/{minh_id}/suspend", json={"reason": "Abuse"}).status_code == 200

    r_book = cust_client.post("/api/bookings", json={"venue_id": 1, "date": "2099-01-01", "start_hour": 10, "hours": 1})
    assert r_book.status_code in (401, 403)
    r_hist = cust_client.get("/api/bookings/my-history")
    assert r_hist.status_code in (401, 403)
    r_cancel = cust_client.post("/api/bookings/BK-000103/cancel")
    assert r_cancel.status_code in (401, 403)


def test_report_review_does_not_unhide_admin_rejected_review(client, db, login):
    rev = _get_review_by_booking_code(db, "BK-000108")
    review_id = rev["id"]
    venue_id = rev["venue_id"]

    login("admin@example.com")
    rej = client.post(f"/api/admin/reviews/{review_id}/moderate", json={"action": "reject"})
    assert rej.status_code == 200

    rejected = _get_review_by_booking_code(db, "BK-000108")
    assert rejected["hidden"] == 1
    assert rejected["moderation_status"] == "rejected"

    # Reporting a rejected review must not unhide it
    rep = client.post(f"/venues/{venue_id}/reviews/{review_id}/report")
    assert rep.status_code == 302
    after_report = _get_review_by_booking_code(db, "BK-000108")
    assert after_report["hidden"] == 1
    assert after_report["moderation_status"] == "rejected"

    # Admin can still restore (approve) the rejected review later
    app_resp = client.post(f"/admin/reviews/{review_id}/moderate", data={"action": "approve"})
    assert app_resp.status_code == 302
    restored = _get_review_by_booking_code(db, "BK-000108")
    assert restored["hidden"] == 0
    assert restored["moderation_status"] == "approved"


# ---------------------------------------------------------------------------
# 7. Stress & boundary tests
# ---------------------------------------------------------------------------

def test_bulk_create_15_users_and_filter_by_role_status_query(client, db, login):
    login("admin@example.com")

    created_ids = []
    for i in range(15):
        role = ("customer", "owner", "admin")[i % 3]
        auto_verify = (i % 5 != 0)  # 3 unverified users (i = 0, 5, 10)
        resp = client.post(
            "/api/admin/users",
            json={
                "email": f"bulk{i:02d}@example.com",
                "password": "Password1",
                "full_name": f"Bulk User {i:02d}",
                "phone": f"09880000{i:02d}",
                "role": role,
                "auto_verify": auto_verify,
            },
        )
        assert resp.status_code == 201
        created_ids.append(resp.get_json()["id"])

    # Suspend 2 bulk users
    assert client.post(f"/api/admin/users/{created_ids[1]}/suspend", json={"reason": "Spam"}).status_code == 200
    assert client.post(f"/api/admin/users/{created_ids[2]}/suspend", json={"reason": "Spam"}).status_code == 200

    with connect(db) as conn:
        all_users = admin.list_users(conn)
        assert len(all_users) == 8 + 15

        owners = admin.list_users(conn, role="owner")
        assert len(owners) == 3 + 5  # 3 seeded + 5 bulk

        suspended = admin.list_users(conn, status="suspended")
        assert len(suspended) == 2

        unverified = admin.list_users(conn, status="unverified")
        assert len(unverified) == 1 + 3  # 1 seeded + 3 bulk

        active_customers = admin.list_users(conn, role="customer", status="active")
        assert all(u["role"] == "customer" and not u["suspended"] and u["email_verified_at"] for u in active_customers)

        q_match = admin.list_users(conn, q="Bulk User 14")
        assert len(q_match) == 1
        assert q_match[0]["email"] == "bulk14@example.com"

        phone_match = admin.list_users(conn, q="0988000007")
        assert len(phone_match) == 1
        assert phone_match[0]["email"] == "bulk07@example.com"


def test_admin_sql_postgres_translation_smoke():
    """Ensure every SQL query in src/admin.py translates cleanly for Postgres via CompatCursor."""
    admin_src = Path(__file__).resolve().parent.parent / "src" / "admin.py"
    tree = ast.parse(admin_src.read_text(encoding="utf-8"))

    sql_strings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            upper = node.value.upper()
            if any(kw in upper for kw in ("SELECT ", "INSERT ", "UPDATE ", "DELETE ")):
                sql_strings.append(node.value)

    assert len(sql_strings) >= 12
    cursor = CompatCursor(None, "postgres")
    for sql in sql_strings:
        param_count = sql.count("?")
        params = tuple(["x"] * param_count) if param_count else ()
        translated, out_params = cursor._translate(sql, params)
        assert "?" not in translated, f"Untranslated ? in: {translated}"
        assert "datetime(" not in translated.lower(), f"Untranslated datetime() in: {translated}"
        assert "strftime(" not in translated.lower(), f"Untranslated strftime() in: {translated}"
        assert len(out_params) == param_count
        # Ensure `user` table references are quoted for Postgres
        if " user " in f" {sql.lower()} ":
            assert '"user"' in translated, f"Unquoted user table in: {translated}"
