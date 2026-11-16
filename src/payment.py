"""Simulated Online QR Payment & Auto-Refund service.

Supports creating a payment session before booking confirmation, rendering a
deterministic 25x25 SVG QR code, simulating QR scan & exact-amount payment
acceptance, confirming the booking with a 6-digit OTP, and automatically
recording refunds when a paid booking is cancelled (BR14, BR15).
"""
import hashlib
import secrets

import booking
import venues
from errors import BusinessRuleError
from time_utils import vn_now

_QR_SIZE = 25


def ensure_payment_table(conn):
    """Create the payment_session table if it does not already exist."""
    is_pg = getattr(conn, "_backend", "sqlite") == "postgres"
    id_col = "id SERIAL,\n            " if is_pg else ""
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS payment_session (
            {id_col}token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            venue_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            start_hour INTEGER NOT NULL,
            hours INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            otp_code TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            paid_amount INTEGER NOT NULL DEFAULT 0,
            refunded_amount INTEGER NOT NULL DEFAULT 0,
            booking_code TEXT,
            created_at TEXT NOT NULL,
            paid_at TEXT,
            refunded_at TEXT
        )
        """
    )
    if is_pg:
        conn.execute("ALTER TABLE payment_session ADD COLUMN IF NOT EXISTS id SERIAL")


def _draw_finder(matrix, reserved, top, left):
    """Place a 7x7 QR finder pattern and its 1-module white separator."""
    for dr in range(-1, 8):
        for dc in range(-1, 8):
            r, c = top + dr, left + dc
            if not (0 <= r < _QR_SIZE and 0 <= c < _QR_SIZE):
                continue
            reserved[r][c] = True
            if 0 <= dr <= 6 and 0 <= dc <= 6:
                is_outer = dr in (0, 6) or dc in (0, 6)
                is_inner = 2 <= dr <= 4 and 2 <= dc <= 4
                matrix[r][c] = 1 if (is_outer or is_inner) else 0
            else:
                matrix[r][c] = 0


def generate_qr_svg(payload_text):
    """Return a deterministic 25x25 QR-style inline SVG for `payload_text`."""
    matrix = [[0] * _QR_SIZE for _ in range(_QR_SIZE)]
    reserved = [[False] * _QR_SIZE for _ in range(_QR_SIZE)]

    _draw_finder(matrix, reserved, 0, 0)
    _draw_finder(matrix, reserved, 0, _QR_SIZE - 7)
    _draw_finder(matrix, reserved, _QR_SIZE - 7, 0)

    for idx in range(8, _QR_SIZE - 8):
        matrix[6][idx] = 1 if idx % 2 == 0 else 0
        reserved[6][idx] = True
        matrix[idx][6] = 1 if idx % 2 == 0 else 0
        reserved[idx][6] = True

    seed_bytes = (payload_text or "").encode("utf-8")
    stream = b""
    counter = 0
    for r in range(_QR_SIZE):
        for c in range(_QR_SIZE):
            if reserved[r][c]:
                continue
            bit_index = r * _QR_SIZE + c
            while len(stream) * 8 <= bit_index:
                stream += hashlib.sha256(seed_bytes + counter.to_bytes(4, "big")).digest()
                counter += 1
            byte_val = stream[bit_index // 8]
            matrix[r][c] = (byte_val >> (bit_index % 8)) & 1

    quiet = 2
    vb = _QR_SIZE + quiet * 2
    paths = [
        f"M{c + quiet},{r + quiet}h1v1h-1z"
        for r in range(_QR_SIZE)
        for c in range(_QR_SIZE)
        if matrix[r][c]
    ]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vb} {vb}" '
        f'width="220" height="220" shape-rendering="crispEdges" '
        f'role="img" aria-label="QR Payment Code">'
        f'<rect width="{vb}" height="{vb}" fill="#ffffff"/>'
        f'<path d="{"".join(paths)}" fill="#0f172a"/>'
        f"</svg>"
    )


def create_session(conn, user, venue_id, day_str, start_hour, hours, now=None):
    """Validate booking slot, compute quote, and persist a new payment session."""
    ensure_payment_table(conn)
    now = now or vn_now()
    venue, d, s, h = booking.check_request(conn, user, venue_id, day_str, start_hour, hours, now)
    amount = booking.quote(conn, venue["id"], d, s, h)["total_price"]

    token = f"PAY-{secrets.token_hex(4).upper()}"
    otp_code = f"{secrets.randbelow(900000) + 100000}"
    created_at = now.strftime("%Y-%m-%d %H:%M:%S")

    conn.execute(
        """
        INSERT INTO payment_session (
            token, user_id, venue_id, booking_date, start_hour, hours,
            amount, otp_code, status, paid_amount, refunded_amount,
            booking_code, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0, 0, NULL, ?)
        """,
        (token, user["id"], venue["id"], d.isoformat(), s, h, amount, otp_code, created_at),
    )
    conn.commit()
    return get_session(conn, token, user)


def get_session(conn, token, user=None):
    """Fetch a payment session with venue details; enforce ownership if `user` is given."""
    ensure_payment_table(conn)
    row = conn.execute(
        """
        SELECT ps.*, v.name AS venue_name, v.area AS venue_area, v.address AS venue_address, v.sport AS sport
        FROM payment_session ps
        JOIN venue v ON v.id = ps.venue_id
        WHERE ps.token = ?
        """,
        (token,),
    ).fetchone()
    if row is None:
        raise BusinessRuleError(404, "Payment session not found")
    if user is not None and row["user_id"] != user["id"]:
        raise BusinessRuleError(403, "You do not have permission to access this payment", "BR14")
    data = dict(row)
    data["area"] = row["venue_area"]
    data["date"] = row["booking_date"]
    start_h = int(row["start_hour"])
    end_h = start_h + int(row["hours"])
    data["time_slot"] = f"{start_h:02d}:00 - {end_h:02d}:00"
    return data


def accept_qr_payment(conn, token, entered_amount_text):
    """Simulate scanning QR and paying the exact quoted amount."""
    ensure_payment_table(conn)
    session = get_session(conn, token)
    entered_amount = venues.parse_price(entered_amount_text)
    if entered_amount is None or entered_amount <= 0:
        raise BusinessRuleError(400, "Please enter a valid payment amount in VND")
    if session["status"] in ("paid", "refunded", "partially_refunded"):
        raise BusinessRuleError(400, "This payment has already been completed")
    if entered_amount != session["amount"]:
        raise BusinessRuleError(
            400, f"Amount mismatch: please enter exact {session['amount']:,} VND"
        )

    conn.execute(
        "UPDATE payment_session SET status = 'accepted', paid_amount = ? WHERE token = ?",
        (entered_amount, token),
    )
    conn.commit()
    return get_session(conn, token)


def confirm_and_book(conn, token, user, entered_otp, now=None):
    """Verify OTP on an accepted payment session and create the booking."""
    now = now or vn_now()
    session = get_session(conn, token, user)
    if session["status"] == "paid" and session["booking_code"]:
        return {"code": session["booking_code"]}
    if session["status"] != "accepted":
        raise BusinessRuleError(400, "Please scan the QR code and accept the payment first")
    if (entered_otp or "").strip() != session["otp_code"]:
        raise BusinessRuleError(
            400, "Invalid confirmation code. Check the code shown after accepting QR payment."
        )

    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    try:
        result = booking.create_booking(
            conn,
            user,
            session["venue_id"],
            session["booking_date"],
            session["start_hour"],
            session["hours"],
            now,
        )
    except BusinessRuleError as exc:
        if exc.status == 409:
            conn.execute(
                """
                UPDATE payment_session
                SET status = 'refunded', refunded_amount = ?, refunded_at = ?
                WHERE token = ?
                """,
                (session["amount"], now_str, token),
            )
            conn.commit()
            raise BusinessRuleError(
                "BR11",
                f"{exc.message}. Your QR payment of {session['amount']:,} VND has been automatically refunded.",
                409,
            ) from exc
        raise
    conn.execute(
        "UPDATE payment_session SET status = 'paid', booking_code = ?, paid_at = ? WHERE token = ?",
        (result["code"], now_str, token),
    )
    conn.commit()
    return result


def auto_refund_for_booking(conn, booking_code, refund_amount, total_price, now=None):
    """Automatically update payment_session refund fields when a booking is cancelled."""
    ensure_payment_table(conn)
    row = conn.execute(
        "SELECT token FROM payment_session WHERE booking_code = ?",
        (booking_code,),
    ).fetchone()
    if row is None:
        return None
    now = now or vn_now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    new_status = "refunded" if refund_amount >= total_price else "partially_refunded"
    conn.execute(
        """
        UPDATE payment_session
        SET refunded_amount = ?, refunded_at = ?, status = ?
        WHERE token = ?
        """,
        (refund_amount, now_str, new_status, row["token"]),
    )
    conn.commit()
    return get_for_booking(conn, booking_code)


def get_for_booking(conn, booking_code):
    """Return the payment_session dict for `booking_code`, or None."""
    ensure_payment_table(conn)
    row = conn.execute(
        "SELECT * FROM payment_session WHERE booking_code = ?",
        (booking_code,),
    ).fetchone()
    return dict(row) if row is not None else None
