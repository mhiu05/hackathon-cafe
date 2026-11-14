"""Read-model builders for the public catalog endpoints (contract: docs/api-contracts.md §2, §9).

Pure functions over a sqlite3 connection. They are the single source of truth for the JSON shapes of
GET /api/cafe, /api/menu, /api/menu/{id} and /api/services and are used by
scripts/contracts/export_fixtures.py to generate contracts/fixtures/*.json.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

# Vietnam is UTC+7 with no DST; a fixed offset avoids needing the `tzdata` package on Windows.
VN_TZ = timezone(timedelta(hours=7), "ICT")
PROFILE_SOURCE_IDS = ("src-photo-service-board", "src-photo-drink-menu", "src-gmaps-listing", "src-tiktok-bibliocafesach",
                      "src-web-mia-2026")
HIGHLIGHT_ATTRIBUTES = (  # (Google Maps attribute group, attribute) shown as highlights, in this order
    ("Nổi tiếng về", "Phù hợp để làm việc trên máy tính xách tay"),
    ("Bầu không khí", "Yên tĩnh"),
    ("Trẻ em", "Phù hợp cho trẻ em"),
    ("Lên kế hoạch", "Nhận đặt chỗ"),
    ("Bãi đỗ xe", "Bãi đỗ xe có tính phí"),
)


def _meta(conn: sqlite3.Connection) -> dict[str, str]:
    return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM kb_meta")}


def source_refs(conn: sqlite3.Connection, ids: tuple[str, ...] | list[str]) -> list[dict]:
    placeholders = ",".join("?" for _ in ids)
    rows = {r["id"]: r for r in conn.execute(
        f"SELECT id, title, url, retrieved_at, verification_status FROM kb_sources WHERE id IN ({placeholders})", list(ids))}
    return [{"source_id": i, "title": rows[i]["title"], "url": rows[i]["url"], "retrieved_at": rows[i]["retrieved_at"],
             "verification_status": rows[i]["verification_status"]} for i in ids if i in rows]


def is_open(open_time: str, close_time: str, now: datetime) -> bool:
    local = now.astimezone(VN_TZ).strftime("%H:%M")
    return open_time <= local < close_time


def cafe_profile_dto(conn: sqlite3.Connection, now: datetime) -> dict:
    row = conn.execute("SELECT * FROM cafe_profile LIMIT 1").fetchone()
    p = json.loads(row["profile_json"])
    attrs = p.get("google_maps_attributes") or {}
    highlights = []
    for group, name in HIGHLIGHT_ATTRIBUTES:
        if any(v.get(name) for v in attrs.get(group, [])):
            highlights.append({"label": name, "source_id": "src-gmaps-listing"})
    highlights += [{"label": "Co-working theo ngày, tuần, tháng", "source_id": "src-photo-service-board"},
                   {"label": "Phòng hội thảo 20–200 người", "source_id": "src-photo-service-board"}]
    snap = p.get("google_maps_snapshot")
    return {
        "branch_id": row["branch_id"], "brand_name": row["brand_name"], "display_name": row["display_name"],
        "address": row["address"], "latitude": row["latitude"], "longitude": row["longitude"],
        "plus_code": p["location"]["plus_code"], "phone": row["phone"],
        "opening_hours": {"open": row["open_time"], "close": row["close_time"], "days_label": "Hằng ngày"},
        "is_open_now": is_open(row["open_time"], row["close_time"], now),
        "channels": {"google_maps_url": p["channels"]["google_maps"]["url"], "facebook_url": p["channels"]["facebook"]["url"],
                     "tiktok_url": p["channels"]["tiktok"]["url"], "website_url": p["channels"]["website"]["url"]},
        "wifi": {"available": bool(p["wifi"]["available"]), "ssid": p["wifi"]["ssid"], "password_policy": "ask_staff"},
        "rating_snapshot": ({"rating": snap["rating"], "reviews_count": snap["reviews_count"], "as_of": snap["as_of"],
                             "source_id": snap["source_id"]} if snap else None),
        "highlights": highlights,
        "data_status": row["data_status"],
        "data_notice": _meta(conn).get("data_notice", ""),
        "sources": source_refs(conn, PROFILE_SOURCE_IDS),
    }


def _variants(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for v in conn.execute("SELECT id, item_id, label, price_vnd FROM menu_item_variants ORDER BY item_id, sort_order"):
        out.setdefault(v["item_id"], []).append({"id": v["id"], "label": v["label"], "price_vnd": v["price_vnd"]})
    return out


def menu_item_dto(row: sqlite3.Row, variants: list[dict]) -> dict:
    prices = [v["price_vnd"] for v in variants] or [row["base_price_vnd"]]
    return {
        "id": row["id"], "category_id": row["category_id"], "name": row["name"],
        "price_vnd": row["base_price_vnd"], "price_min_vnd": min(prices), "price_max_vnd": max(prices), "variants": variants,
        "availability": row["availability"], "availability_note": row["availability_note"],
        "is_orderable": bool(row["is_orderable"]), "price_verified": bool(row["price_verified"]),
        "description": row["description"], "needs_review": json.loads(row["needs_review_json"]),
        "suggested_tags": json.loads(row["suggested_tags_json"]),
    }


def menu_response_dto(conn: sqlite3.Connection) -> dict:
    meta = _meta(conn)
    variants = _variants(conn)
    items = [menu_item_dto(r, variants.get(r["id"], [])) for r in conn.execute(
        "SELECT i.* FROM menu_items i JOIN menu_categories c ON c.id = i.category_id ORDER BY c.sort_order, i.sort_order")]
    counts: dict[str, int] = {}
    for i in items:
        counts[i["category_id"]] = counts.get(i["category_id"], 0) + 1
    categories = [{"id": c["id"], "name": c["name"], "kind": c["kind"], "sort_order": c["sort_order"], "item_count": counts.get(c["id"], 0)}
                  for c in conn.execute("SELECT * FROM menu_categories ORDER BY sort_order")]
    return {"as_of": meta.get("menu_as_of", ""), "price_basis": meta.get("menu_price_basis", ""), "categories": categories, "items": items}


def services_response_dto(conn: sqlite3.Connection) -> dict:
    meta = _meta(conn)
    packages = [{"id": r["id"], "label": r["label"], "duration_days": r["duration_days"], "price_vnd": r["price_vnd"],
                 "includes_vat": bool(r["includes_vat"]), "price_verified": bool(r["price_verified"])}
                for r in conn.execute("SELECT * FROM coworking_packages ORDER BY sort_order")]
    rooms = [{"id": r["id"], "name": r["name"], "area_m2": r["area_m2"], "capacity_max": r["capacity_max"],
              "capacity_theater": r["capacity_theater"], "capacity_tables": r["capacity_tables"], "layout_note": r["layout_note"],
              "session_hours": r["session_hours"], "price_vnd": r["price_vnd"], "includes_vat": bool(r["includes_vat"]),
              "price_verified": bool(r["price_verified"])}
             for r in conn.execute("SELECT * FROM meeting_rooms ORDER BY sort_order")]
    facts = [{"id": r["id"], "scope": r["scope"], "kind": r["kind"], "label": r["label"], "price_from_vnd": r["price_from_vnd"],
              "price_to_vnd": r["price_to_vnd"], "unit": r["unit"], "note": r["note"]}
             for r in conn.execute("SELECT * FROM service_facts ORDER BY scope, kind, sort_order")]
    return {"as_of": meta.get("services_as_of", ""), "price_basis": meta.get("services_price_basis", ""),
            "coworking_packages": packages, "meeting_rooms": rooms, "facts": facts, "booking_policy": meta.get("booking_policy", "")}

