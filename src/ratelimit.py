"""Thread-safe in-memory sliding-window HTTP rate limiter for auth endpoints."""
import threading
import time
from collections import defaultdict, deque

from flask import current_app, jsonify, render_template, request

RATE_LIMITED_ENDPOINTS = {
    "/login": "auth_login",
    "/register": "auth_register",
    "/forgot-password": "auth_forgot_password",
    "/reset-password": "auth_reset_password",
    "/account/password": "auth_change_password",
    "/api/auth/login": "auth_login",
    "/api/auth/register": "auth_register",
}

DEFAULT_LIMIT = 20
DEFAULT_WINDOW_SECONDS = 60
_MAX_TRACKED_KEYS = 2048


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window counter keyed by (client_ip, endpoint_group)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._hits = defaultdict(deque)

    def _prune_expired_locked(self, cutoff):
        stale = [k for k, dq in self._hits.items() if not dq or dq[-1] <= cutoff]
        for k in stale:
            del self._hits[k]

    def is_allowed(self, key, limit=DEFAULT_LIMIT, window_seconds=DEFAULT_WINDOW_SECONDS, now=None):
        """Record a request for key and return True if within limit, False otherwise."""
        ts = time.monotonic() if now is None else now
        cutoff = ts - window_seconds
        with self._lock:
            if len(self._hits) > _MAX_TRACKED_KEYS:
                self._prune_expired_locked(cutoff)
            bucket = self._hits[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(ts)
            return True

    def reset(self):
        """Clear all recorded request timestamps."""
        with self._lock:
            self._hits.clear()


def _client_ip():
    # Use socket peer address (or ProxyFix-resolved remote_addr) so clients cannot
    # spoof X-Forwarded-For to bypass rate limits.
    return request.remote_addr or "unknown"


def init_ratelimit(app):
    """Attach a per-app SlidingWindowRateLimiter and before_request check."""
    limiter = SlidingWindowRateLimiter()
    app.extensions["ratelimit"] = limiter

    @app.before_request
    def check_rate_limit():
        if request.method != "POST":
            return None
        group = RATE_LIMITED_ENDPOINTS.get(request.path)
        if not group:
            return None
        if current_app.config.get("TESTING") and not current_app.config.get("RATELIMIT_ENABLED"):
            return None

        limit = int(current_app.config.get("RATELIMIT_MAX_REQUESTS", DEFAULT_LIMIT))
        window = int(current_app.config.get("RATELIMIT_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS))
        if not limiter.is_allowed((_client_ip(), group), limit=limit, window_seconds=window):
            message = "Too many requests. Please try again later."
            if request.path.startswith("/api/"):
                return jsonify(error=message), 429
            return render_template("error.html", message=message), 429
        return None
