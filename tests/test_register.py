"""US01 - Customer registration (#14): BR1, BR2, BR3, BR4."""
import re
from datetime import datetime, timedelta

import pytest

from auth import make_verify_token
from db import connect

HOA = {"email": "hoa.nguyen@gmail.com", "password": "sanbong2026",
       "full_name": "Nguyen Thi Hoa", "phone": "0912345678"}
TOO_SHORT = "sanbong"

def register(client, **changes):
    return client.post("/register", data={**HOA, **changes})


def user_row(db, email):
    with connect(db) as conn:
        return conn.execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()


def test_new_customer_is_created_and_sent_to_login(client, db):
    # US01 criterion 1
    response = register(client)
    assert response.status_code == 302
    assert response.headers["Location"] == "/login"
    user = user_row(db, "hoa.nguyen@gmail.com")
    assert user["full_name"] == "Nguyen Thi Hoa"
    assert user["role"] == "customer"
    assert user["email_verified_at"] is None          # BR4: cannot book yet
    page = client.get("/login").get_data(as_text=True)
    assert "We sent a verification link to hoa.nguyen@gmail.com" in page


def test_same_email_twice_is_refused(client, db):
    # US01 criterion 2, BR1 - also with different capital letters
    register(client)
    response = register(client, email="Hoa.Nguyen@gmail.com")
    assert response.status_code == 409
    assert "This email is already in use" in response.get_data(as_text=True)
    with connect(db) as conn:
        n = conn.execute("SELECT COUNT(*) FROM user WHERE email = 'hoa.nguyen@gmail.com'").fetchone()[0]
    assert n == 1


def test_short_password_keeps_the_other_fields(client):
    # US01 criterion 3, BR2
    page = register(client, **{"password": TOO_SHORT}).get_data(as_text=True)
    assert "Password must be at least 8 characters" in page
    assert 'value="Nguyen Thi Hoa"' in page
    assert 'value="hoa.nguyen@gmail.com"' in page


@pytest.mark.parametrize("password, accepted", [("12345678", False), ("sanbongg", False), ("sanbong1", True)])
def test_password_needs_a_letter_and_a_digit(client, password, accepted):
    # BR2 worked examples
    response = register(client, password=password)
    assert (response.status_code == 302) == accepted
    if not accepted:
        assert "Password must contain at least one letter and one digit" in response.get_data(as_text=True)


@pytest.mark.parametrize("phone, message", [
    ("091234567", "Phone number must be 10 digits"),
    ("1912345678", "Phone number must start with 0"),
])
def test_phone_must_be_ten_digits_starting_with_zero(client, phone, message):
    # US01 criterion 4, BR3
    response = register(client, phone=phone)
    assert response.status_code == 400
    assert message in response.get_data(as_text=True)


def test_verification_link_verifies_the_account(client, db):
    # US01 criterion 1, BR4: the link shown on screen is the one that was "sent"
    register(client)
    page = client.get("/login").get_data(as_text=True)
    link = re.search(r'href="(http://localhost/verify\?token=[^"]+)"', page).group(1)
    response = client.get(link.replace("http://localhost", ""))
    assert response.status_code == 200
    assert "Your email is verified" in response.get_data(as_text=True)
    assert user_row(db, "hoa.nguyen@gmail.com")["email_verified_at"] is not None


def test_link_older_than_24_hours_has_expired(client, db):
    # US01 criterion 5, BR4
    register(client)
    user_id = user_row(db, "hoa.nguyen@gmail.com")["id"]
    secret = client.application.config["SECRET_KEY"]
    token = make_verify_token(secret, user_id, datetime.now() - timedelta(hours=24, minutes=1))
    response = client.get(f"/verify?token={token}")
    assert response.status_code == 410
    assert "This verification link has expired" in response.get_data(as_text=True)
    assert user_row(db, "hoa.nguyen@gmail.com")["email_verified_at"] is None


def test_tampered_link_is_refused(client):
    response = client.get("/verify?token=not-a-real-token")
    assert response.status_code == 404
    assert "This verification link is not valid" in response.get_data(as_text=True)


def test_unverified_customer_is_asked_to_verify_and_can_get_a_new_link(client, login):
    register(client)
    login("hoa.nguyen@gmail.com", "sanbong2026")
    assert "Please verify your email before booking" in client.get("/dashboard").get_data(as_text=True)
    page = client.post("/verify/resend", follow_redirects=True).get_data(as_text=True)
    assert "We sent a new verification link" in page
    assert "/verify?token=" in page


def test_api_register_returns_201_then_409(client):
    # design.md section 3, endpoint 1
    first = client.post("/api/auth/register", json=HOA)
    assert first.status_code == 201
    assert "user_id" in first.get_json()
    second = client.post("/api/auth/register", json=HOA)
    assert second.status_code == 409
    assert second.get_json() == {"error": "This email is already in use", "rule": "BR1"}
