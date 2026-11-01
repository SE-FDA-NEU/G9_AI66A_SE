"""US01 Customer Registration and US02 User Login - automated test cases (TC-01 .. TC-76).

Types: N = normal, E = error, B = boundary.

Rules covered (from src/auth.py):
  BR1 unique email (409)         BR2 password >= 8 chars with a letter and a digit (400)
  BR3 phone = 10 digits, starts with 0 (400)      BR4 verification link lasts 24 hours (404 / 410)
  BR5 5th wrong password locks the account for 15 minutes (423)
  BR6 wrong email and wrong password give the same message (401)
  BR7 landing page by role (auth.LANDING_PAGE)

Fixtures come from tests/conftest.py: db, client, login (seeded accounts use password sanbong1).
Tests marked "service" call auth.* with a fixed clock so exact time boundaries can be checked
without waiting.
"""
from datetime import datetime, timedelta

import pytest
from werkzeug.security import check_password_hash

import auth                                   # src/auth.py (rules, tokens, LANDING_PAGE)
from db import connect
from errors import BusinessRuleError

NOW = datetime(2026, 10, 11, 9, 0)
SEED_PASS = "sanbong1"
CUSTOMER = "minh@example.com"
OWNER = "lan.owner@example.com"
WRONG_PASS = "wrong-pass1"

VALID = {"email": "newcustomer@example.com", "password": "matkhau123",
         "full_name": "Pham Van An", "phone": "0912345678"}

PW_TOO_SHORT = "abc123"        # 6 characters
PW_ONE_SHORT = "abcdef1"       # 7 characters
PW_SHORTEST_OK = "abcdefg1"    # 8 characters: letter + digit

# ---- helpers ----------------------------------------------------------------------------
def register(client, **changes):
    return client.post("/register", data={**VALID, **changes})


def sign_in(client, email, password=SEED_PASS, **extra):
    return client.post("/login", data={"email": email, "password": password, **extra})


def find_user(db, email):
    with connect(db) as conn:
        return conn.execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()


def count_users(db):
    with connect(db) as conn:
        return conn.execute("SELECT COUNT(*) FROM user").fetchone()[0]


def set_user(db, email, **columns):
    sets = ", ".join(f"{c} = ?" for c in columns)
    with connect(db) as conn:
        conn.execute(f"UPDATE user SET {sets} WHERE email = ?", (*columns.values(), email))


def email_with(db, role, verified=True):
    clause = "IS NOT NULL" if verified else "IS NULL"
    with connect(db) as conn:
        row = conn.execute(f"SELECT email FROM user WHERE role = ? AND email_verified_at {clause}",
                           (role,)).fetchone()
    if row is None:
        pytest.skip(f"no seeded {role} (verified={verified})")
    return row["email"]


def signed_in_id(client):
    with client.session_transaction() as s:
        return s.get("user_id")


def flashes(client):
    with client.session_transaction() as s:
        return [tuple(f) for f in s.get("_flashes", [])]


def secret(client):
    return client.application.config["SECRET_KEY"]


def token_for(client, user_id, issued=None):
    return auth.make_verify_token(secret(client), user_id, issued or datetime.now())


def wrong_sign_ins(client, email, times):
    for _ in range(times):
        response = sign_in(client, email, WRONG_PASS)
    return response


def fail_sign_ins(db, email, times, now=NOW):
    """Service-level: `times` wrong passwords at a fixed clock."""
    with connect(db) as conn:
        for _ in range(times):
            with pytest.raises(BusinessRuleError):
                auth.sign_in(conn, email, WRONG_PASS, now)


# =========================================================================================
# US01 - CUSTOMER REGISTRATION
# =========================================================================================

# ---- Normal -----------------------------------------------------------------------------
def test_TC01_register_with_valid_data_redirects_to_login(client, db):
    """TC-01 (N) Valid details create the account and send the user to /login."""
    response = register(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert find_user(db, VALID["email"]) is not None


def test_TC02_new_account_is_a_customer(client, db):
    """TC-02 (N) A self-registered user is a customer, never an owner or admin."""
    register(client)
    assert find_user(db, VALID["email"])["role"] == "customer"


def test_TC03_password_is_stored_hashed(client, db):
    """TC-03 (N) The plain password is not stored; the hash matches it."""
    register(client)
    stored = find_user(db, VALID["email"])["password_hash"]
    assert VALID["password"] not in stored
    assert check_password_hash(stored, VALID["password"])


def test_TC04_success_message_and_verification_link_are_flashed(client):
    """TC-04 (N) After registering the user sees the success message and the verify link."""
    register(client)
    messages = flashes(client)
    assert any(cat == "success" and "Account created" in msg for cat, msg in messages)
    assert any(cat == "verify-link" and "/verify?token=" in msg for cat, msg in messages)


def test_TC05_new_account_starts_unverified(client, db):
    """TC-05 (N) BR4: the email is unverified until the link is used."""
    register(client)
    assert find_user(db, VALID["email"])["email_verified_at"] is None


def test_TC06_verification_link_verifies_the_email(client, db):
    """TC-06 (N) A valid token marks the email as verified."""
    register(client)
    user = find_user(db, VALID["email"])
    response = client.get(f"/verify?token={token_for(client, user['id'])}")
    assert response.status_code == 200
    assert find_user(db, VALID["email"])["email_verified_at"] is not None


def test_TC07_new_customer_can_sign_in_and_lands_on_the_dashboard(client):
    """TC-07 (N) The account created through the form can sign in."""
    register(client)
    response = sign_in(client, VALID["email"], VALID["password"])
    assert response.status_code == 302
    assert response.headers["Location"].endswith(auth.LANDING_PAGE["customer"])


def test_TC08_api_register_returns_201_and_the_user_id(client, db):
    """TC-08 (N) POST /api/auth/register creates the account."""
    response = client.post("/api/auth/register", json=VALID)
    assert response.status_code == 201
    assert response.get_json()["user_id"] == find_user(db, VALID["email"])["id"]


def test_TC09_resend_sends_a_new_link_to_an_unverified_user(client):
    """TC-09 (N) A signed-in unverified customer can ask for a fresh link."""
    register(client)
    sign_in(client, VALID["email"], VALID["password"])
    response = client.post("/verify/resend")
    assert response.status_code == 302
    assert any("new verification link" in msg for _, msg in flashes(client))


def test_TC10_resend_for_a_verified_user_says_already_verified(client, db):
    """TC-10 (N) No new link is sent when the email is already verified."""
    sign_in(client, email_with(db, "customer", verified=True))
    client.post("/verify/resend")
    assert any("already verified" in msg for _, msg in flashes(client))


def test_TC11_verifying_twice_keeps_the_first_timestamp(client, db):
    """TC-11 (N, service) Using the link a second time changes nothing."""
    register(client)
    user_id = find_user(db, VALID["email"])["id"]
    token = auth.make_verify_token(secret(client), user_id, NOW)
    with connect(db) as conn:
        auth.verify_email(conn, secret(client), token, NOW + timedelta(hours=1))
        auth.verify_email(conn, secret(client), token, NOW + timedelta(hours=2))
    assert find_user(db, VALID["email"])["email_verified_at"] == "2026-10-11 10:00:00"


# ---- Error ------------------------------------------------------------------------------
def test_TC12_duplicate_email_is_refused_with_409(client, db):
    """TC-12 (E) BR1: an email that already exists cannot register again."""
    before = count_users(db)
    response = register(client, email=CUSTOMER)
    assert response.status_code == 409
    assert "This email is already in use" in response.get_data(as_text=True)
    assert count_users(db) == before


@pytest.mark.parametrize("email", ["", "plainaddress", "no-at.example.com", "@example.com",
                                   "user@", "user@@example.com", "us er@example.com", "user@nodot"])
def test_TC13_invalid_email_is_refused_with_400(client, db, email):
    """TC-13 (E) Empty or malformed emails are refused and nothing is saved."""
    before = count_users(db)
    response = register(client, email=email)
    assert response.status_code == 400
    assert "Please enter a valid email address" in response.get_data(as_text=True)
    assert count_users(db) == before


def test_TC14_password_shorter_than_8_is_refused(client, db):
    """TC-14 (E) BR2: fewer than 8 characters."""
    response = register(client, password=PW_TOO_SHORT)
    assert response.status_code == 400
    assert "Password must be at least 8 characters" in response.get_data(as_text=True)
    assert find_user(db, VALID["email"]) is None


@pytest.mark.parametrize("password", ["abcdefgh", "12345678", "ABCDEFGH", "!!!!!!!!"])
def test_TC15_password_without_a_letter_and_a_digit_is_refused(client, db, password):
    """TC-15 (E) BR2: 8+ characters but letters only, digits only or symbols only."""
    response = register(client, password=password)
    assert response.status_code == 400
    assert "at least one letter and one digit" in response.get_data(as_text=True)
    assert find_user(db, VALID["email"]) is None


@pytest.mark.parametrize("name", ["", "   "])
def test_TC16_blank_full_name_is_refused(client, db, name):
    """TC-16 (E) The name is required (spaces only counts as empty)."""
    response = register(client, full_name=name)
    assert response.status_code == 400
    assert "Please enter your full name" in response.get_data(as_text=True)
    assert find_user(db, VALID["email"]) is None


@pytest.mark.parametrize("phone", ["", "abcdefghij", "09123-45678", "0912 345 678",
                                   "+84912345678", "091234567"])
def test_TC17_phone_that_is_not_10_digits_is_refused(client, db, phone):
    """TC-17 (E) BR3: letters, symbols, spaces, +84 prefix or a wrong length."""
    response = register(client, phone=phone)
    assert response.status_code == 400
    assert "Phone number must be 10 digits" in response.get_data(as_text=True)
    assert find_user(db, VALID["email"]) is None


def test_TC18_phone_not_starting_with_0_is_refused(client, db):
    """TC-18 (E) BR3: 10 digits but the first one is not 0."""
    response = register(client, phone="1234567890")
    assert response.status_code == 400
    assert "Phone number must start with 0" in response.get_data(as_text=True)
    assert find_user(db, VALID["email"]) is None


def test_TC19_empty_form_shows_every_message_at_once(client, db):
    """TC-19 (E) US01 criterion 3: all four problems are listed in one go."""
    before = count_users(db)
    response = client.post("/register", data={"email": "", "password": "", "full_name": "", "phone": ""})
    page = response.get_data(as_text=True)
    assert response.status_code == 400
    for message in ("Please enter a valid email address", "Password must be at least 8 characters",
                    "Please enter your full name", "Phone number must be 10 digits"):
        assert message in page
    assert count_users(db) == before


def test_TC20_error_keeps_what_the_user_typed_but_not_the_password(client):
    """TC-20 (E) US01 criterion 3: values are kept; the password is never sent back."""
    page = register(client, phone="abc").get_data(as_text=True)
    assert f'value="{VALID["full_name"]}"' in page
    assert f'value="{VALID["email"]}"' in page
    assert VALID["password"] not in page


def test_TC21_sql_injection_in_email_is_harmless(client, db):
    """TC-21 (E) Injection text is refused and the user table is untouched."""
    before = count_users(db)
    assert register(client, email="a'; DROP TABLE user;--@example.com").status_code in (400, 409)
    assert count_users(db) == before


def test_TC22_garbage_verification_token_is_refused_with_404(client):
    """TC-22 (E) BR4: a made-up token verifies nobody."""
    response = client.get("/verify?token=not-a-real-token")
    assert response.status_code == 404
    assert "not valid" in response.get_data(as_text=True)


def test_TC23_token_signed_with_another_secret_is_refused(client, db):
    """TC-23 (E) A forged token for someone else's account is rejected."""
    user_id = find_user(db, CUSTOMER)["id"]
    forged = auth.make_verify_token("some-other-secret", user_id, datetime.now())
    assert client.get(f"/verify?token={forged}").status_code == 404


def test_TC24_expired_verification_link_is_refused_with_410(client, db):
    """TC-24 (E) BR4: a link older than 24 hours has expired."""
    register(client)
    user_id = find_user(db, VALID["email"])["id"]
    old = token_for(client, user_id, datetime.now() - timedelta(hours=25))
    response = client.get(f"/verify?token={old}")
    assert response.status_code == 410
    assert "expired" in response.get_data(as_text=True)
    assert find_user(db, VALID["email"])["email_verified_at"] is None


def test_TC25_api_register_duplicate_returns_409_json(client, db):
    """TC-25 (E) The API refuses an existing email and answers in JSON."""
    before = count_users(db)
    response = client.post("/api/auth/register", json={**VALID, "email": CUSTOMER})
    assert response.status_code == 409
    assert response.get_json() is not None
    assert count_users(db) == before


def test_TC26_api_register_with_a_short_password_returns_400(client, db):
    """TC-26 (E) The API applies the same rules as the form."""
    response = client.post("/api/auth/register", json={**VALID, "password": PW_TOO_SHORT})
    assert response.status_code == 400
    assert find_user(db, VALID["email"]) is None


def test_TC27_resend_verification_requires_sign_in(client):
    """TC-27 (E) A visitor cannot ask for a new verification link."""
    response = client.post("/verify/resend")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# ---- Boundary ---------------------------------------------------------------------------
def test_TC28_password_of_exactly_8_with_letter_and_digit_is_accepted(client):
    """TC-28 (B) BR2: the shortest valid password."""
    assert register(client, password=PW_SHORTEST_OK).status_code == 302


def test_TC29_password_of_7_with_letter_and_digit_is_refused(client, db):
    """TC-29 (B) BR2: one character short."""
    assert register(client, password=PW_ONE_SHORT).status_code == 400
    assert find_user(db, VALID["email"]) is None


def test_TC30_very_long_password_is_accepted_without_error(client):
    """TC-30 (B) No maximum is defined in BR2, so 1,000 characters must not crash."""
    long_value = "a" * 999 + "1"
    assert register(client, password=long_value).status_code == 302
    assert sign_in(client, VALID["email"], long_value).status_code == 302


def test_TC31_one_character_name_is_accepted(client):
    """TC-31 (B) The only name rule is 'not empty'."""
    assert register(client, full_name="A").status_code == 302


def test_TC32_phone_of_exactly_10_digits_starting_with_0_is_accepted(client):
    """TC-32 (B) BR3: the valid shape."""
    assert register(client, phone="0000000000").status_code == 302


def test_TC33_phone_with_9_or_11_digits_is_refused(client, db):
    """TC-33 (B) BR3: one digit short, one digit over."""
    assert register(client, phone="012345678").status_code == 400
    assert register(client, phone="01234567890").status_code == 400
    assert find_user(db, VALID["email"]) is None


def test_TC34_spaces_around_the_email_are_trimmed(client, db):
    """TC-34 (B) '  email  ' is stored as 'email'."""
    register(client, email=f"  {VALID['email']}  ")
    assert find_user(db, VALID["email"]) is not None


def test_TC35_verification_link_is_still_valid_at_exactly_24_hours(client, db):
    """TC-35 (B, service) BR4: the limit is 'more than 24 hours'."""
    user_id = find_user(db, CUSTOMER)["id"]
    token = auth.make_verify_token(secret(client), user_id, NOW)
    with connect(db) as conn:
        assert auth.verify_email(conn, secret(client), token, NOW + timedelta(hours=24)) == user_id


def test_TC36_verification_link_expires_one_second_after_24_hours(client, db):
    """TC-36 (B, service) BR4: 24h + 1s is too late."""
    user_id = find_user(db, CUSTOMER)["id"]
    token = auth.make_verify_token(secret(client), user_id, NOW)
    with connect(db) as conn, pytest.raises(BusinessRuleError) as e:
        auth.verify_email(conn, secret(client), token, NOW + timedelta(hours=24, seconds=1))
    assert e.value.status == 410


# =========================================================================================
# US02 - USER LOGIN
# =========================================================================================

# ---- Normal -----------------------------------------------------------------------------
def test_TC37_customer_lands_on_the_dashboard(client):
    """TC-37 (N) BR7: a customer goes to /dashboard."""
    response = sign_in(client, CUSTOMER)
    assert response.status_code == 302
    assert response.headers["Location"].endswith(auth.LANDING_PAGE["customer"])
    assert client.get("/dashboard").status_code == 200


def test_TC38_owner_lands_on_the_owner_area(client):
    """TC-38 (N) BR7: an owner goes to their venues."""
    response = sign_in(client, OWNER)
    assert response.headers["Location"].endswith(auth.LANDING_PAGE["owner"])
    assert client.get("/owner/venues").status_code == 200


def test_TC39_admin_lands_on_the_admin_page(client, db):
    """TC-39 (N) BR7: an administrator goes to /admin."""
    response = sign_in(client, email_with(db, "admin"))
    assert response.headers["Location"].endswith(auth.LANDING_PAGE["admin"])
    assert client.get("/admin").status_code == 200


def test_TC40_session_is_created_after_login(client):
    """TC-40 (N) The session holds the user id."""
    sign_in(client, CUSTOMER)
    assert signed_in_id(client)


def test_TC41_login_fixture_signs_in_a_seeded_account(client, login):
    """TC-41 (N) The shared fixture works for an owner."""
    assert login(OWNER).status_code == 302
    assert client.get("/owner/venues").status_code == 200


def test_TC42_sign_out_ends_the_session(client):
    """TC-42 (N) POST /logout clears the session and returns to /search."""
    sign_in(client, OWNER)
    response = client.post("/logout")
    assert response.status_code == 302 and response.headers["Location"].endswith("/search")
    assert not signed_in_id(client)
    assert client.get("/owner/venues").status_code == 302


def test_TC43_api_login_returns_role_and_landing_page(client):
    """TC-43 (N) JSON API login."""
    response = client.post("/api/auth/login", json={"email": OWNER, "password": SEED_PASS})
    assert response.status_code == 200
    assert response.get_json() == {"role": "owner", "redirect": auth.LANDING_PAGE["owner"]}


def test_TC44_api_logout_returns_204(client):
    """TC-44 (N) JSON API logout."""
    client.post("/api/auth/login", json={"email": CUSTOMER, "password": SEED_PASS})
    assert client.post("/api/auth/logout").status_code == 204
    assert not signed_in_id(client)


def test_TC45_signed_in_user_opening_login_goes_to_their_landing_page(client):
    """TC-45 (N) GET /login when already signed in redirects."""
    sign_in(client, CUSTOMER)
    response = client.get("/login")
    assert response.status_code == 302
    assert response.headers["Location"].endswith(auth.LANDING_PAGE["customer"])


def test_TC46_login_returns_to_the_page_the_user_was_on(client):
    """TC-46 (N) After an expired session the user goes back via ?next=."""
    assert sign_in(client, CUSTOMER, next="/search").headers["Location"].endswith("/search")


def test_TC47_successful_login_resets_the_failed_counter(client, db):
    """TC-47 (N) BR5: the counter goes back to 0."""
    wrong_sign_ins(client, CUSTOMER, 3)
    assert find_user(db, CUSTOMER)["failed_login_count"] == 3
    sign_in(client, CUSTOMER)
    assert find_user(db, CUSTOMER)["failed_login_count"] == 0


# ---- Error ------------------------------------------------------------------------------
def test_TC48_wrong_password_is_refused_with_401(client):
    """TC-48 (E) BR6: wrong password, generic message, no session."""
    response = sign_in(client, CUSTOMER, WRONG_PASS)
    assert response.status_code == 401
    assert auth.WRONG_SIGN_IN in response.get_data(as_text=True)
    assert not signed_in_id(client)


def test_TC49_unknown_email_is_refused_with_the_same_message(client):
    """TC-49 (E) BR6: an unknown email gets the same 401 and sentence."""
    response = sign_in(client, "nobody@example.com", "whatever123")
    assert response.status_code == 401
    assert auth.WRONG_SIGN_IN in response.get_data(as_text=True)
    assert not signed_in_id(client)


def test_TC50_wrong_email_and_wrong_password_look_the_same(client):
    """TC-50 (E) BR6: nothing reveals which emails exist."""
    a = sign_in(client, "nobody@example.com", "whatever123")
    b = sign_in(client, CUSTOMER, WRONG_PASS)
    assert a.status_code == b.status_code == 401

    def without_emails(response):
        page = response.get_data(as_text=True)
        return page.replace("nobody@example.com", "").replace(CUSTOMER, "")

    assert without_emails(a) == without_emails(b)


@pytest.mark.parametrize("email,password", [("", SEED_PASS), (CUSTOMER, ""), ("", "")])
def test_TC51_empty_fields_are_refused(client, email, password):
    """TC-51 (E) Empty email and/or password do not sign in."""
    assert sign_in(client, email, password).status_code == 401
    assert not signed_in_id(client)


def test_TC52_password_is_case_sensitive(client):
    """TC-52 (E) SANBONG1 is not sanbong1."""
    assert sign_in(client, CUSTOMER, SEED_PASS.upper()).status_code == 401
    assert not signed_in_id(client)


def test_TC53_protected_page_redirects_a_visitor_to_login_with_next(client):
    """TC-53 (E) A signed-out visitor is sent to /login?next=<page>."""
    response = client.get("/owner/venues/new")
    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login?next=")


def test_TC54_customer_cannot_open_the_owner_area(client):
    """TC-54 (E) BR7: a customer gets 403 on owner pages."""
    sign_in(client, CUSTOMER)
    assert client.get("/owner/venues").status_code == 403


def test_TC55_api_login_with_wrong_password_returns_401_json(client):
    """TC-55 (E) The API refuses bad credentials and sets no session."""
    response = client.post("/api/auth/login", json={"email": CUSTOMER, "password": "nope"})
    assert response.status_code == 401
    assert response.get_json() is not None
    assert not signed_in_id(client)


def test_TC56_sql_injection_in_login_is_harmless(client):
    """TC-56 (E) ' OR '1'='1 does not bypass the password check."""
    assert sign_in(client, "' OR '1'='1", "' OR '1'='1").status_code == 401
    assert not signed_in_id(client)


@pytest.mark.parametrize("target", ["//evil.example.com", "https://evil.example.com", "evil.com"])
def test_TC57_next_cannot_send_the_user_to_another_website(client, target):
    """TC-57 (E) safe_next: only paths on this site are followed."""
    response = sign_in(client, CUSTOMER, next=target)
    assert response.headers["Location"].endswith(auth.LANDING_PAGE["customer"])


def test_TC58_failed_login_keeps_the_email_but_not_the_password(client):
    """TC-58 (E) The form is refilled with the email only."""
    page = sign_in(client, CUSTOMER, WRONG_PASS).get_data(as_text=True)
    assert CUSTOMER in page
    assert WRONG_PASS not in page


def test_TC59_unverified_customer_can_sign_in_but_cannot_book(client):
    """TC-59 (E) BR4: login works, booking is blocked until the email is verified."""
    register(client)
    assert sign_in(client, VALID["email"], VALID["password"]).status_code == 302
    page = client.get("/booking/1")
    assert page.status_code == 403
    assert "verify your email" in page.get_data(as_text=True)


def test_TC60_booking_page_sends_a_visitor_to_login(client):
    """TC-60 (E) /booking/1 needs a session."""
    response = client.get("/booking/1")
    assert response.status_code == 302
    assert response.headers["Location"] == "/login?next=/booking/1"


def test_TC61_fifth_wrong_password_locks_the_account(client):
    """TC-61 (E) BR5: the 5th wrong password in a row gives 423 and the locked message."""
    response = wrong_sign_ins(client, CUSTOMER, 5)
    assert response.status_code == 423
    assert auth.LOCKED in response.get_data(as_text=True)


def test_TC62_locked_account_refuses_even_the_correct_password(client):
    """TC-62 (E) BR5: while locked, the right password does not get in."""
    wrong_sign_ins(client, CUSTOMER, 5)
    response = sign_in(client, CUSTOMER, SEED_PASS)
    assert response.status_code == 423
    assert not signed_in_id(client)


def test_TC63_api_login_reports_a_locked_account_with_423(client):
    """TC-63 (E) The API applies BR5 too."""
    wrong_sign_ins(client, CUSTOMER, 5)
    response = client.post("/api/auth/login", json={"email": CUSTOMER, "password": SEED_PASS})
    assert response.status_code == 423
    assert response.get_json() is not None


def test_TC64_unknown_email_never_locks_anything(client, db):
    """TC-64 (E) Six attempts with an unknown email stay 401 and change no account."""
    before = count_users(db)
    assert wrong_sign_ins(client, "nobody@example.com", 6).status_code == 401
    assert count_users(db) == before


# ---- Boundary ---------------------------------------------------------------------------
def test_TC65_four_wrong_passwords_do_not_lock(client, db):
    """TC-65 (B) BR5: the 4th failure is still a plain 401, counter = 4."""
    assert wrong_sign_ins(client, CUSTOMER, 4).status_code == 401
    user = find_user(db, CUSTOMER)
    assert user["failed_login_count"] == 4 and not user["locked_until"]


def test_TC66_correct_password_after_four_failures_signs_in(client, db):
    """TC-66 (B) BR5: the account is not locked at 4 and the counter resets."""
    wrong_sign_ins(client, CUSTOMER, 4)
    assert sign_in(client, CUSTOMER).status_code == 302
    assert find_user(db, CUSTOMER)["failed_login_count"] == 0


def test_TC67_locking_sets_locked_until_and_resets_the_counter(client, db):
    """TC-67 (B) BR5: at the 5th failure locked_until is set and the counter goes to 0."""
    wrong_sign_ins(client, CUSTOMER, 5)
    user = find_user(db, CUSTOMER)
    assert user["locked_until"] is not None
    assert user["failed_login_count"] == 0


def test_TC68_lock_ends_exactly_15_minutes_later(client, db):
    """TC-68 (B, service) BR5: at the moment the lock expires the user can sign in."""
    fail_sign_ins(db, CUSTOMER, 5)
    with connect(db) as conn:
        user = auth.sign_in(conn, CUSTOMER, SEED_PASS, NOW + auth.LOCK_TIME)
    assert user["email"] == CUSTOMER


def test_TC69_account_is_still_locked_one_second_before_the_lock_ends(client, db):
    """TC-69 (B, service) BR5: 14 min 59 s after locking is still locked."""
    fail_sign_ins(db, CUSTOMER, 5)
    with connect(db) as conn, pytest.raises(BusinessRuleError) as e:
        auth.sign_in(conn, CUSTOMER, SEED_PASS, NOW + auth.LOCK_TIME - timedelta(seconds=1))
    assert e.value.status == 423


def test_TC70_an_expired_lock_does_not_block_and_is_cleared(client, db):
    """TC-70 (B) A locked_until in the past is ignored, and the next sign-in clears it."""
    set_user(db, CUSTOMER, locked_until="2000-01-01 00:00:00")
    assert sign_in(client, CUSTOMER).status_code == 302
    assert find_user(db, CUSTOMER)["locked_until"] is None


def test_TC71_spaces_around_the_email_are_ignored_at_login(client):
    """TC-71 (B) '  minh@example.com  ' still signs in."""
    sign_in(client, f"  {CUSTOMER}  ")
    assert signed_in_id(client)


def test_TC72_very_long_password_is_refused_without_a_server_error(client):
    """TC-72 (B) 10,000 characters gets a clean 401, not a 500."""
    assert sign_in(client, CUSTOMER, "a" * 10000).status_code == 401
    assert not signed_in_id(client)


def test_TC73_leading_space_in_the_password_is_not_trimmed(client):
    """TC-73 (B) ' sanbong1' is a different password."""
    assert sign_in(client, CUSTOMER, " " + SEED_PASS).status_code == 401
    assert not signed_in_id(client)


def test_TC74_second_login_replaces_the_first_session(client):
    """TC-74 (B) Signing in as another user switches cleanly."""
    sign_in(client, CUSTOMER)
    first = signed_in_id(client)
    sign_in(client, OWNER)
    assert signed_in_id(client) != first
    assert client.get("/owner/venues").status_code == 200


def test_TC75_register_then_login_with_the_boundary_password(client):
    """TC-75 (B) US01 -> US02 end to end with the shortest valid password."""
    register(client, password=PW_SHORTEST_OK)
    assert sign_in(client, VALID["email"], PW_SHORTEST_OK).status_code == 302
    assert signed_in_id(client)


def test_TC76_registering_does_not_sign_the_user_in(client):
    """TC-76 (B) Register sends the user to /login; no session until they sign in."""
    register(client)
    assert not signed_in_id(client)
