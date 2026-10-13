"""US02 - User login (#15): BR5, BR6, BR7, BR8, BR14."""
from datetime import datetime, timedelta

from db import connect


def test_customer_lands_on_their_page_and_sees_their_name(client, login):
    # US02 criterion 1, BR7
    response = login("minh@example.com")
    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard"
    page = client.get("/dashboard").get_data(as_text=True)
    assert "Pham Duc Minh" in page


def test_owner_lands_in_venue_management(login):
    # US02 criterion 4, BR7
    assert login("lan.owner@example.com").headers["Location"] == "/owner/venues"


def test_admin_lands_in_the_admin_area(login):
    # BR7
    assert login("admin@example.com").headers["Location"] == "/admin"


def test_wrong_password_and_unknown_email_get_the_same_message(login):
    # US02 criterion 3, BR6
    wrong_password = login("minh@example.com", "wrongpass1")
    unknown_email = login("nobody@example.com", "wrongpass1")
    assert wrong_password.status_code == unknown_email.status_code == 401
    for response in (wrong_password, unknown_email):
        assert "Email or password is incorrect" in response.get_data(as_text=True)


def test_fifth_wrong_password_locks_the_account(db, login):
    # US02 criterion 2, BR5
    for _ in range(4):
        assert login("minh@example.com", "wrongpass1").status_code == 401
    fifth = login("minh@example.com", "wrongpass1")
    assert fifth.status_code == 423
    assert "Account temporarily locked. Try again in 15 minutes" in fifth.get_data(as_text=True)
    # while locked, even the right password is refused
    assert login("minh@example.com").status_code == 423


def test_lock_ends_after_15_minutes_and_counter_resets(db, login):
    # BR5: pretend the lock started 16 minutes ago
    for _ in range(5):
        login("minh@example.com", "wrongpass1")
    past = (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    with connect(db) as conn:
        conn.execute("UPDATE user SET locked_until = ? WHERE email = 'minh@example.com'", (past,))
    assert login("minh@example.com").status_code == 302
    with connect(db) as conn:
        row = conn.execute("SELECT failed_login_count, locked_until FROM user"
                           " WHERE email = 'minh@example.com'").fetchone()
    assert tuple(row) == (0, None)


def test_session_expires_after_30_minutes_idle(client, login):
    # US02 criterion 5, BR8
    login("minh@example.com")
    with client.session_transaction() as session:
        session["last_seen"] = (datetime.now() - timedelta(minutes=31)).isoformat()
    response = client.get("/dashboard", follow_redirects=True)
    page = response.get_data(as_text=True)
    assert response.request.path == "/login"
    assert "Your session has expired" in page


def test_session_still_valid_after_29_minutes(client, login):
    # BR8: the limit is 30 minutes, not less
    login("minh@example.com")
    with client.session_transaction() as session:
        session["last_seen"] = (datetime.now() - timedelta(minutes=29)).isoformat()
    assert client.get("/dashboard").status_code == 200


def test_signed_out_visitor_is_sent_to_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_customer_cannot_open_the_owner_area(client, login):
    # BR14
    login("minh@example.com")
    response = client.get("/owner/venues")
    assert response.status_code == 403
    assert "You do not have permission to access this page" in response.get_data(as_text=True)


def test_sign_out_ends_the_session(client, login):
    login("minh@example.com")
    client.post("/logout")
    assert client.get("/dashboard").status_code == 302


def test_api_login_returns_role_and_landing_page(client):
    # design.md section 3, endpoint 3
    response = client.post("/api/auth/login", json={"email": "lan.owner@example.com", "password": "sanbong1"})
    assert response.status_code == 200
    assert response.get_json() == {"role": "owner", "redirect": "/owner/venues"}


def test_api_login_error_names_the_rule(client):
    response = client.post("/api/auth/login", json={"email": "minh@example.com", "password": "nope12345"})
    assert response.status_code == 401
    assert response.get_json() == {"error": "Email or password is incorrect", "rule": "BR6"}
