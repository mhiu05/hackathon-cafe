"""Deterministic study/work session planner behind the `plan_visit` agent tool.

Compares the ways to spend N hours at the café for P people — common area + drinks, the co-working day
package, a meeting room — using only SQL prices, and checks the plan against opening hours.
Nothing here is a booking or an availability check.
"""
from __future__ import annotations

import math
import re
import sqlite3
from datetime import datetime

from app.catalog.dto import VN_TZ, services_response_dto
from app.catalog.repository import recommend_items

NEED_LABELS = {"private_room": "phòng riêng", "projector": "máy chiếu", "fixed_seat": "chỗ ngồi cố định", "power_outlet": "ổ cắm điện"}
# Which verified amenity label (service_facts, scope → label) satisfies each need.
NEED_AMENITY = {"projector": "Máy chiếu", "fixed_seat": "Chỗ ngồi cố định", "power_outlet": "Ổ cắm điện"}
ROOM_MIN_GROUP = 5
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"


def _timing(open_time: str, close_time: str, start: str, hours: float) -> dict:
    start_m, open_m, close_m = _minutes(start), _minutes(open_time), _minutes(close_time)
    end_m = start_m + round(hours * 60)
    fits = open_m <= start_m and end_m <= close_m
    timing = {"start": start, "end": _hhmm(end_m), "open": open_time, "close": close_time, "fits_opening_hours": fits}
    if start_m < open_m:
        timing["warning"] = f"Quán mở cửa lúc {open_time}; bạn nên bắt đầu từ {open_time}."
    elif start_m >= close_m:
        timing["warning"] = f"Quán đóng cửa lúc {close_time}; khung giờ này quán đã đóng."
    elif end_m > close_m:
        left = (close_m - start_m) / 60
        timing["warning"] = f"Quán đóng cửa lúc {close_time}; từ {start} bạn chỉ ngồi được khoảng {left:g} tiếng."
        timing["max_hours_from_start"] = round(left, 2)
    return timing


def _needs_status(needs: list[str], amenities: set[str], *, private: bool) -> tuple[list[str], list[str], list[str]]:
    met, unmet, unknown = [], [], []
    for need in needs:
        if need == "private_room":
            (met if private else unmet).append(NEED_LABELS[need])
        elif NEED_AMENITY[need] in amenities:
            met.append(NEED_LABELS[need])
        else:
            unknown.append(NEED_LABELS[need])
    return met, unmet, unknown


def plan_visit(conn: sqlite3.Connection, *, hours: float, people: int, budget_per_person_vnd: int | None,
               start_time: str | None, needs: list[str], now: datetime) -> dict:
    if start_time is not None and not _HHMM.match(start_time):
        raise ValueError("start_time must be HH:MM")
    profile = conn.execute("SELECT open_time, close_time FROM cafe_profile LIMIT 1").fetchone()
    start = start_time or now.astimezone(VN_TZ).strftime("%H:%M")
    services = services_response_dto(conn)
    amenities = {scope: {f["label"] for f in services["facts"] if f["kind"] == "amenity" and f["scope"] == scope}
                 for scope in ("coworking", "meeting_room")}
    options: list[dict] = []

    drinks = recommend_items(conn, preferences=[], max_price_vnd=None, include_food=False, exclude_item_ids=[], limit=3)
    if drinks:
        cheapest = drinks[0]["price_min_vnd"]
        met, unmet, unknown = _needs_status(needs, set(), private=False)
        # A shared table cannot be "fixed" — treat that need as not met rather than unknown.
        if "fixed_seat" in needs:
            unknown.remove(NEED_LABELS["fixed_seat"]); unmet.append(NEED_LABELS["fixed_seat"])
        options.append({"kind": "common_area", "label": "Ngồi khu chung và gọi đồ uống",
            "per_person_vnd": cheapest, "total_vnd": cheapest * people,
            "cost_basis": "Ước tính tối thiểu 1 đồ uống rẻ nhất mỗi người; quán chưa công bố phí ngồi hay giới hạn thời gian.",
            "cheapest_drinks": [{"item_id": d["item_id"], "name": d["name"], "price_min_vnd": d["price_min_vnd"]} for d in drinks],
            "needs_met": met, "needs_unmet": unmet, "needs_unverified": unknown})

    day = next((p for p in services["coworking_packages"] if p["duration_days"] == 1), None)
    if day:
        met, unmet, unknown = _needs_status(needs, amenities["coworking"], private=False)
        options.append({"kind": "coworking_day", "label": f"Gói co-working {day['label']}", "package_id": day["id"],
            "per_person_vnd": day["price_vnd"], "total_vnd": day["price_vnd"] * people,
            "cost_basis": "Giá gói/người theo bảng giá tại quán; đồ uống tính riêng.",
            "includes": sorted(amenities["coworking"]), "needs_met": met, "needs_unmet": unmet, "needs_unverified": unknown})

    # A 20+ seat room is only worth listing for a group, or when the guest explicitly needs a room/projector.
    wants_room = people >= ROOM_MIN_GROUP or bool({"private_room", "projector"} & set(needs))
    rooms = [r for r in services["meeting_rooms"] if wants_room and (r["capacity_tables"] or r["capacity_max"] or 0) >= people]
    for room in sorted(rooms, key=lambda r: r["price_vnd"])[:2]:
        sessions = math.ceil(hours / room["session_hours"])
        total = room["price_vnd"] * sessions
        met, unmet, unknown = _needs_status(needs, amenities["meeting_room"], private=True)
        options.append({"kind": "meeting_room", "label": f"Thuê {room['name']} ({room['layout_note']})", "room_id": room["id"],
            "sessions": sessions, "session_hours": room["session_hours"], "per_person_vnd": math.ceil(total / people),
            "total_vnd": total, "cost_basis": f"{sessions} ca × {room['session_hours']} tiếng; chưa gồm đồ uống, teabreak.",
            "includes": sorted(amenities["meeting_room"]), "needs_met": met, "needs_unmet": unmet, "needs_unverified": unknown})

    for option in options:
        option["within_budget"] = None if budget_per_person_vnd is None else option["per_person_vnd"] <= budget_per_person_vnd
    # Options that verifiably satisfy every stated need first, then unverified ones, then the cheapest per person.
    options.sort(key=lambda o: (bool(o["needs_unmet"]), bool(o["needs_unverified"]), o["per_person_vnd"]))
    return {"request": {"hours": hours, "people": people, "budget_per_person_vnd": budget_per_person_vnd,
                        "needs": [NEED_LABELS[n] for n in needs]},
            "timing": _timing(profile["open_time"], profile["close_time"], start, hours),
            "options": options,
            "price_basis": services["price_basis"], "booking_policy": services["booking_policy"],
            "notes": ["Gợi ý tham khảo, không phải đặt chỗ; phòng trống và chỗ ngồi cần hỏi nhân viên."]}
