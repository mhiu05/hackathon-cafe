from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import time
from collections import defaultdict, deque

from app.errors import ApiError
from app.settings import Settings
from app.timeutil import add_minutes, utc_now


class LoginRateLimiter:
    def __init__(self, max_failures: int = 5, window_s: float = 60):
        self.max_failures, self.window_s = max_failures, window_s
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def check(self, ip: str) -> None:
        entries = self._failures[ip]
        cutoff = time.monotonic() - self.window_s
        while entries and entries[0] <= cutoff:
            entries.popleft()
        if len(entries) >= self.max_failures:
            raise ApiError(429, "RATE_LIMITED", "Bạn thử quá nhiều lần, vui lòng đợi một phút.")

    def record_failure(self, ip: str) -> None:
        self._failures[ip].append(time.monotonic())


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def login(conn: sqlite3.Connection, settings: Settings, pin: str, client_ip: str, limiter: LoginRateLimiter) -> dict:
    if len(settings.admin_pin) < 6:
        raise ApiError(503, "ADMIN_NOT_CONFIGURED", "Quán chưa cấu hình PIN quản trị.")
    limiter.check(client_ip)
    if not hmac.compare_digest(pin.encode(), settings.admin_pin.encode()):
        limiter.record_failure(client_ip)
        raise ApiError(401, "ADMIN_AUTH_REQUIRED", "PIN không đúng.")
    token, now = secrets.token_urlsafe(32), utc_now()
    expires_at = add_minutes(now, 12 * 60)
    conn.execute("INSERT INTO admin_sessions(token_hash,created_at,expires_at) VALUES (?,?,?)", (_token_hash(token), now, expires_at))
    return {"token": token, "expires_at": expires_at}


def verify(conn: sqlite3.Connection, token: str) -> None:
    row = conn.execute("SELECT expires_at FROM admin_sessions WHERE token_hash=?", (_token_hash(token),)).fetchone()
    if row is None or row["expires_at"] <= utc_now():
        raise ApiError(401, "ADMIN_AUTH_REQUIRED", "Vui lòng đăng nhập quản trị.")


def logout(conn: sqlite3.Connection, token: str) -> None:
    conn.execute("DELETE FROM admin_sessions WHERE token_hash=?", (_token_hash(token),))
