"""Tests for US11 (US24: Venue owner sets peak-hour pricing).
Business Rules: BR12, BR13.
"""
from datetime import datetime
import pytest
from db import connect
import pricing


def test_pricing_requires_owner_role(client, login):
    # Customer gets 403
    login("minh@example.com")
    res = client.get("/owner/venues/1/pricing")
    assert res.status_code == 403


def test_owner_adds_peak_pricing_rule(client, login, db):
    # US11: Owner adds peak rule on Friday (4) from 18:00 to 20:00 at 450,000 VND
    login("lan.owner@example.com")
    res = client.post("/owner/venues/1/pricing", data={
        "weekday": 4,
        "start_hour": 18,
        "end_hour": 20,
        "price_per_hour": "450,000"
    }, follow_redirects=True)
    assert res.status_code == 200
    page = res.get_data(as_text=True)
    assert "Peak pricing rule added successfully!" in page
    assert "450,000 VND" in page


def test_overlapping_pricing_rule_on_same_weekday_is_refused(client, login, db):
    # BR12: Rules must not overlap on the same venue and weekday
    login("lan.owner@example.com")

    with connect(db) as conn:
        pricing.add_pricing_rule(conn, 1, 0, 17, 20, 400000)

    # Try to add rule overlapping 18:00-21:00 on Monday (0)
    res = client.post("/owner/venues/1/pricing", data={
        "weekday": 0,
        "start_hour": 18,
        "end_hour": 21,
        "price_per_hour": "450,000"
    }, follow_redirects=True)
    assert res.status_code == 200
    page = res.get_data(as_text=True)
    assert "cannot overlap" in page


def test_owner_deletes_pricing_rule(client, login, db):
    # US11: Delete rule
    login("lan.owner@example.com")

    with connect(db) as conn:
        rule_id = pricing.add_pricing_rule(conn, 1, 5, 8, 10, 350000)

    res = client.post(f"/owner/venues/1/pricing/{rule_id}/delete", follow_redirects=True)
    assert res.status_code == 200
    page = res.get_data(as_text=True)
    assert "Pricing rule deleted successfully" in page
