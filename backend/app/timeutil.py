from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def add_minutes(ts: str, minutes: int) -> str:
    return (parse_ts(ts) + timedelta(minutes=minutes)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
