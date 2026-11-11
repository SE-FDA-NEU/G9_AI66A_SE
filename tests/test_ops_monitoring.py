"""Operations and monitoring test suite for Milestone 5.

Verifies:
1. /health returns 200 with JSON status="ok" and venue count when healthy.
2. /health returns 503 Service Unavailable when the database connection fails.
3. Response headers, JSON formatting, and error-handling behavior for production.
4. Unauthenticated public access for uptime pingers (Vercel, Render, UptimeRobot).
"""
import time
from unittest.mock import patch


def test_health_returns_200_and_seeded_venues_count(client):
    """Normal case: /health returns 200 and proves database reachability."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.is_json
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "venues" in data
    assert data["venues"] >= 24


def test_health_returns_503_when_database_connection_fails(client):
    """Error case: /health returns 503 when the database throws an exception."""
    with patch("app.get_db") as mock_get_db:
        mock_get_db.side_effect = RuntimeError("Database unreachable")
        resp = client.get("/health")
        assert resp.status_code == 503
        assert resp.is_json
        data = resp.get_json()
        assert data["status"] == "error"
        assert "Database connection failure" in data["error"]


def test_health_endpoint_headers_and_performance(client):
    """Performance & headers: /health must return application/json rapidly."""
    t0 = time.perf_counter()
    resp = client.get("/health")
    elapsed = time.perf_counter() - t0

    assert resp.status_code == 200
    assert "application/json" in resp.headers.get("Content-Type", "")
    # Health checks should return in under 250ms locally
    assert elapsed < 0.250


def test_health_accessible_without_authentication(client):
    """Uptime robots and external monitoring services must not be redirected."""
    resp = client.get("/health", follow_redirects=False)
    assert resp.status_code == 200
    assert resp.location is None


def test_api_404_returns_json_and_web_returns_html(client):
    """Error routing: /api/* returns JSON errors; web routes return friendly HTML."""
    api_resp = client.get("/api/nonexistent-route-for-testing")
    assert api_resp.status_code == 404
    assert api_resp.is_json
    assert api_resp.get_json() == {"error": "Not found"}

    web_resp = client.get("/nonexistent-web-page-route")
    assert web_resp.status_code == 404
    assert "text/html" in web_resp.headers.get("Content-Type", "")
    assert "We could not find that page" in web_resp.get_data(as_text=True)
