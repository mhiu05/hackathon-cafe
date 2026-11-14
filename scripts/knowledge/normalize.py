"""Normalize all collected knowledge into canonical files under data/knowledge/normalized/.

    uv run python scripts/knowledge/normalize.py

Inputs (read-only): biblio_cafe_kb_bundle/*.json, data/knowledge/curated/*.json, data/knowledge/raw/apify/*/
Outputs: cafe_profile.json, menu.json, services.json, documents.jsonl, source_manifest.json,
         events.json, social_insights.json, unverified_claims.json, and data/knowledge/knowledge_extended.md

Deterministic: same inputs -> byte-identical outputs (no timestamps except those carried from sources).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import (  # noqa: E402
    BRAND_ID, BRANCH_ID, BUNDLE_DIR, CURATED_DIR, KNOWLEDGE_DIR, NORMALIZED_DIR, RAW_APIFY_DIR,
    read_json, write_json, write_jsonl,
)

from app.knowledge.text import content_hash, fold_vi, normalize_text  # noqa: E402

GMAPS_URL = (
    "https://www.google.com/maps/place/Biblio+Book+Cafe+-+79+Ng%E1%BB%A5y+Nh%C6%B0+Kon+Tum/@21.0013374,105.8029646,17z"
)
TIKTOK_ACCOUNT_URL = "https://www.tiktok.com/@bibliocafesach"
INGESTIBLE = {"owner_verified", "verified_branch", "brand_general", "conflicting"}

CATEGORIES = {  # printed name -> (slug, kind, sort)
    "Cà phê": ("ca-phe", "drink", 1),
    "Sữa chua & cacao": ("sua-chua-cacao", "drink", 2),
    "Trà lạnh": ("tra-lanh", "drink", 3),
    "Nước ép": ("nuoc-ep", "drink", 4),
    "Matcha": ("matcha", "drink", 5),
    "Sinh tố": ("sinh-to", "drink", 6),
    "Mì tôm": ("mi-tom", "food", 7),
    "Bánh bao": ("banh-bao", "food", 8),
    "Ăn vặt": ("an-vat", "food", 9),
}

# Inferred recommendation tags. Basis is the printed item/category NAME only — never verified facts.
TAG_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("ca-phe", ("cà phê", "bạc xỉu", "cold brew")),
    ("co-caffeine", ("cà phê", "bạc xỉu", "cold brew", "matcha", "olong")),
    ("matcha", ("matcha",)),
    ("trai-cay", ("vải", "đào", "cam", "xoài", "chanh leo", "dưa hấu", "dừa tươi", "việt quất", "quýt", "mãng cầu",
                  "hoa quả", "nhiệt đới", "quả mọng", "dứa", "sinh tố bơ", "bơ già")),
    ("vi-chua", ("chanh", "quýt", "cam", "sữa chua", "việt quất")),
    ("beo-ngay", ("cốt dừa", "kem chesse", "sữa chua", "bạc xỉu", "ca cao", "cacao", "sinh tố bơ", "bơ già", "latte", "cookie")),
    ("hoa-thao-moc", ("hoa hồng", "hoa thảo mộc", "atiso", "gừng", "sả", "mật ong", "sen")),
    ("co-topping", ("trân châu", "thạch", "nha đam", "kem chesse")),
    ("sua-chua", ("sữa chua",)),
    ("ca-cao", ("ca cao", "cacao")),
]
CATEGORY_TAGS = {
    "tra-lanh": ["tra", "lanh"], "nuoc-ep": ["nuoc-ep"], "sinh-to": ["sinh-to"], "mi-tom": ["an-no"],
    "banh-bao": ["an-no"], "an-vat": ["an-vat"],
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", fold_vi(text)).strip("-")


def infer_tags(name: str, category_slug: str) -> list[str]:
    low = normalize_text(name).lower()
    tags = [t for t, needles in TAG_RULES if any(n in low for n in needles)]
    if "cold brew" in low:
        tags.append("lanh")
    for t in CATEGORY_TAGS.get(category_slug, []):
        if t not in tags:
            tags.append(t)
    return sorted(set(tags))


def source_for_images(image_ids: list[int]) -> str:
    return "src-photo-food-menu" if set(image_ids) <= {2, 3} else "src-photo-drink-menu"


# ----------------------------------------------------------------------------------------------- menu

def build_menu(bundle_menu: dict) -> dict:
    categories = [
        {"id": s, "name": name, "kind": kind, "sort_order": order}
        for name, (s, kind, order) in sorted(CATEGORIES.items(), key=lambda kv: kv[1][2])
    ]
    items = []
    for order, raw in enumerate(bundle_menu["items"], start=1):
        cat_slug, _, _ = CATEGORIES[raw["category"]]
        variants: list[dict] = []
        base_price = raw.get("price_vnd")
        if raw.get("variants"):
            variants = [
                {"id": f"{raw['id']}:{slug(v['label'])}", "label": v["label"], "price_vnd": int(v["price_vnd"]), "sort_order": i}
                for i, v in enumerate(raw["variants"], start=1)
            ]
            base_price = None
        elif raw["id"] == "menu_001":
            # Printed as one line 'CAFE NÂU / ĐEN' at one price -> two explicit variants (bundle note).
            variants = [
                {"id": "menu_001:nau", "label": "Nâu", "price_vnd": int(raw["price_vnd"]), "sort_order": 1},
                {"id": "menu_001:den", "label": "Đen", "price_vnd": int(raw["price_vnd"]), "sort_order": 2},
            ]
            base_price = None
        needs_review = list(raw.get("needs_review") or [])
        availability_note = None
        if raw.get("handwritten_cross_on_menu"):
            availability_note = "Ảnh menu có dấu X viết tay cạnh tên món; chưa xác định là hết hàng — cần nhân viên xác nhận."
        prices = [v["price_vnd"] for v in variants] or [base_price]
        items.append({
            "id": raw["id"],
            "category_id": cat_slug,
            "name": raw["name"],
            "name_search": fold_vi(raw["name"]),
            "base_price_vnd": base_price,
            "price_min_vnd": min(prices),
            "price_max_vnd": max(prices),
            "variants": variants,
            "availability": raw.get("availability", "unknown"),
            "availability_note": availability_note,
            "is_orderable": True,
            "price_verified": bool(raw.get("verified_current_price", False)),
            "description": None,
            "note": raw.get("note"),
            "needs_review": needs_review,
            "suggested_tags": infer_tags(raw["name"], cat_slug),
            "source_id": source_for_images(raw.get("source_image_ids") or []),
            "sort_order": order,
        })
    return {
        "branch_id": BRANCH_ID,
        "as_of": bundle_menu["as_of"],
        "currency": "VND",
        "price_basis": "Giá niêm yết trên ảnh menu chụp tại quán ngày 14/11/2026; chưa được quán xác nhận là giá hiện hành.",
        "suggested_tags_basis": "INFERRED from the printed item/category name only. Not verified ingredients, sweetness, caffeine or nutrition.",
        "tag_glossary": {
            "ca-phe": "đồ uống cà phê", "co-caffeine": "tên món gợi ý có cà phê/matcha/olong (suy luận)", "matcha": "có matcha",
            "trai-cay": "tên món có trái cây", "vi-chua": "tên món gợi ý vị chua (chanh, quýt, cam, sữa chua…) — suy luận",
            "beo-ngay": "tên món gợi ý béo (cốt dừa, kem, sữa chua, ca cao…) — suy luận", "hoa-thao-moc": "hoa/thảo mộc",
            "co-topping": "có topping trong tên (trân châu, thạch, nha đam, kem)", "sua-chua": "sữa chua", "ca-cao": "ca cao",
            "tra": "nhóm trà", "lanh": "đồ uống lạnh theo tên nhóm/món", "nuoc-ep": "nước ép", "sinh-to": "sinh tố",
            "an-no": "món ăn no (mì, bánh bao)", "an-vat": "ăn vặt",
        },
        "categories": categories,
        "items": items,
        "review_flags": bundle_menu.get("review_flags", []),
    }


# ------------------------------------------------------------------------------------------- services

def build_services(bundle_services: dict) -> dict:
    cw = bundle_services["coworking"]
    durations = {"1 ngày": 1, "1 tuần": 7, "1 tháng": 30}
    slugs = {"1 ngày": "cowork-1-day", "1 tuần": "cowork-1-week", "1 tháng": "cowork-1-month"}
    packages = [
        {"id": slugs[p["label"]], "label": p["label"], "duration_days": durations[p["label"]], "price_vnd": int(p["price_vnd"]),
         "includes_vat": bool(cw["prices_include_10_percent_vat"]), "price_verified": False, "source_id": "src-photo-service-board",
         "sort_order": i}
        for i, p in enumerate(cw["packages"], start=1)
    ]
    ms = bundle_services["meeting_spaces"]
    rooms = []
    for i, r in enumerate(ms["rooms"], start=1):
        theater = r.get("capacity_theater_people")
        tables = r.get("capacity_tables_and_chairs_people")
        meeting = r.get("capacity_meeting_people")
        generic = r.get("capacity_people")
        cap_max = max(c for c in (theater, tables, meeting, generic) if c)
        if theater:
            note = f"Ngồi ghế tối đa {theater} người; có cả bàn và ghế tối đa {tables} người"
        elif meeting:
            note = f"{meeting} người, {r.get('layout', '').lower()}"
        else:
            note = f"{generic} người, {r.get('layout', '').lower()}"
        rooms.append({
            "id": "cafe-space" if r["name"] == "Không gian cafe" else f"room-{r['name'].split()[-1]}",
            "name": r["name"], "area_m2": r["area_m2"], "capacity_max": cap_max,
            "capacity_theater": theater, "capacity_tables": tables or meeting, "layout_note": note,
            "session_hours": r["session_hours"], "price_vnd": int(r["price_vnd"]),
            "includes_vat": bool(ms["prices_include_10_percent_vat"]), "price_verified": False,
            "source_id": "src-photo-service-board", "sort_order": i,
        })
    facts = []
    for i, label in enumerate(cw["amenities"], start=1):
        facts.append({"id": f"cowork-amenity-{i:02d}", "scope": "coworking", "kind": "amenity", "label": label,
                      "price_from_vnd": None, "price_to_vnd": None, "unit": None, "note": None,
                      "verification_status": "verified_branch", "source_id": "src-photo-service-board", "sort_order": i})
    for i, label in enumerate(ms["included_facilities"], start=1):
        facts.append({"id": f"room-facility-{i:02d}", "scope": "meeting_room", "kind": "amenity", "label": label,
                      "price_from_vnd": None, "price_to_vnd": None, "unit": None, "note": None,
                      "verification_status": "verified_branch", "source_id": "src-photo-service-board", "sort_order": i})
    for i, svc in enumerate(ms["additional_services"], start=1):
        lo = svc.get("price_from_vnd") or (svc.get("price_range_vnd") or [None, None])[0] or svc.get("price_vnd")
        hi = (svc.get("price_range_vnd") or [None, None])[1]
        facts.append({"id": f"room-extra-{i:02d}", "scope": "meeting_room", "kind": "extra_service", "label": svc["name"],
                      "price_from_vnd": lo, "price_to_vnd": hi, "unit": svc.get("unit"), "note": svc.get("note"),
                      "verification_status": "verified_branch", "source_id": "src-photo-service-board", "sort_order": i})
    facts.append({"id": "room-policy-availability", "scope": "meeting_room", "kind": "policy",
                  "label": "Không có dữ liệu phòng trống; trợ lý không nhận đặt phòng — liên hệ quán 0976 214 224.",
                  "price_from_vnd": None, "price_to_vnd": None, "unit": None, "note": None,
                  "verification_status": "verified_branch", "source_id": "src-kb-curation", "sort_order": 99})
    return {
        "branch_id": BRANCH_ID, "as_of": bundle_services["as_of"],
        "price_basis": "Bảng giá chụp tại quán ngày 14/11/2026; giá đã gồm 10% VAT theo bảng; chưa được quán xác nhận là hiện hành.",
        "coworking_packages": packages, "meeting_rooms": rooms, "service_facts": facts,
        "review_flags": bundle_services.get("review_flags", []),
    }


# -------------------------------------------------------------------------------------- cafe profile

def build_profile(gmaps: dict | None, bundle_services: dict) -> dict:
    snapshot = None
    if gmaps:
        snapshot = {"rating": gmaps.get("totalScore"), "reviews_count": gmaps.get("reviewsCount"),
                    "distribution": gmaps.get("reviewsDistribution"), "price_bucket": gmaps.get("price"),
                    "as_of": "2026-11-14", "source_id": "src-gmaps-listing"}
    return {
        "branch_id": BRANCH_ID,
        "brand_name": "Biblio",
        "display_name": "Biblio Café Sách — 79 Ngụy Như Kon Tum",
        "data_status": "user_provided_unverified",
        "names_seen": [
            {"value": "BIBLIO CAFE SÁCH", "source_id": "src-photo-drink-menu"},
            {"value": "BIBLIO BOOKS COFFEE (logo)", "source_id": "src-photo-drink-menu"},
            {"value": "Biblio Book Cafe - 79 Ngụy Như Kon Tum", "source_id": "src-gmaps-listing"},
            {"value": "Biblio - Cafe Sách Ngụy Như Kon Tum", "source_id": "src-facebook-page"},
        ],
        "address": {"value": "79 Ngụy Như Kon Tum, Làng sinh viên Hacinco, Thanh Xuân, Hà Nội",
                    "sources": ["src-photo-service-board", "src-gmaps-listing", "src-tiktok-bibliocafesach", "src-web-mia-2026"],
                    "verification_status": "verified_branch",
                    "conflicts": [{"value": "Cổng 1 - 79 Ngụy Như Kon Tum", "source_id": "src-web-tadiha-2022"},
                                  {"value": "99 Ngụy Như Kon Tum ('Cafe sách Đông Tây')", "source_id": "src-web-traveloka"}]},
        "location": {"latitude": 21.0013374, "longitude": 105.8029646, "plus_code": "2R23+G5 Thanh Xuân, Hà Nội",
                     "source_id": "src-gmaps-listing"},
        "phone": {"value": "0976 214 224", "sources": ["src-photo-service-board", "src-tiktok-bibliocafesach"],
                  "verification_status": "verified_branch",
                  "conflicts": [{"value": "024 2215 7878", "source_id": "src-web-tadiha-2022", "note": "2022, stale"}]},
        "opening_hours": {"open": "07:00", "close": "22:30", "days": "hằng ngày",
                          "sources": ["src-photo-drink-menu", "src-tiktok-bibliocafesach", "src-web-mia-2026", "src-web-1000libraries-2026"],
                          "verification_status": "verified_branch",
                          "conflicts": [{"value": "07:00–23:00", "source_id": "src-web-tadiha-2022", "note": "2022, stale"}]},
        "channels": {
            "google_maps": {"url": GMAPS_URL, "place_id": (gmaps or {}).get("placeId"), "source_id": "src-gmaps-listing"},
            "facebook": {"url": "https://www.facebook.com/Khonggianvanhoadongtay/", "name": "Biblio - Cafe Sách Ngụy Như Kon Tum",
                         "verification_status": "verified_branch", "source_id": "src-facebook-page"},
            "tiktok": {"url": TIKTOK_ACCOUNT_URL, "handle": "@bibliocafesach", "verification_status": "verified_branch",
                       "note": "Self-identifies the branch address/phone in a caption; not confirmed by staff.", "source_id": "src-tiktok-bibliocafesach"},
            "website": {"url": None, "note": "No official website found (2026-11-14)."},
            "email": {"value": "cafesachbiblio@gmail.com", "verification_status": "unverified_branch", "source_id": "src-web-tadiha-2022",
                      "note": "Brand email from a 2022 article; not confirmed."},
        },
        "wifi": {"available": True, "ssid": "BIBLIO CAFE SACH", "password": None,
                 "note": "Password intentionally not stored; ask staff.", "source_id": "src-photo-drink-menu"},
        "google_maps_snapshot": snapshot,
        "google_maps_attributes": (gmaps or {}).get("additionalInfo") or {},
        "service_board_contact": bundle_services.get("contact_from_board"),
    }


# ---------------------------------------------------------------------------------------- documents

def doc(id_: str, title: str, category: str, kind: str, source_id: str, content: str, *, status: str, source_type: str,
        url: str | None, retrieved_at: str, branch_id: str = BRANCH_ID, metadata: dict | None = None) -> dict:
    text = normalize_text(content)
    return {"id": id_, "title": normalize_text(title), "content": text, "category": category, "branch_id": branch_id,
            "source_id": source_id, "source_type": source_type, "source_url": url, "verification_status": status,
            "content_kind": kind, "retrieved_at": retrieved_at, "content_hash": content_hash(text), "metadata": metadata or {}}


def fmt_vnd(v: int) -> str:
    return f"{v:,}".replace(",", ".") + "đ"


def build_documents(menu: dict, services: dict, gmaps: dict | None, gmaps_meta: dict | None, tiktok: list[dict],
                    tiktok_meta: dict | None, curated: dict, synthesis: dict, sources: dict[str, dict]) -> list[dict]:
    photo_at = "2026-11-14T03:13:18.000Z"
    docs: list[dict] = [
        doc("doc-photo-contact", "Địa chỉ và điện thoại in trên bảng dịch vụ tại quán", "location", "fact", "src-photo-service-board",
            "Bảng giá dịch vụ chụp tại quán ngày 14/11/2026 ghi địa chỉ: 79 Ngụy Như Kon Tum, Thanh Xuân, Hà Nội và số điện thoại "
            "0976 214 224. Tên in trên menu: BIBLIO CAFE SÁCH, logo BIBLIO BOOKS COFFEE. Quán nằm trong khuôn viên Làng sinh viên Hacinco.",
            status="verified_branch", source_type="user_photo", url=None, retrieved_at=photo_at),
        doc("doc-photo-hours-wifi", "Giờ mở cửa và Wi-Fi in trên menu đồ uống", "opening_hours", "fact", "src-photo-drink-menu",
            "Menu đồ uống chụp tại quán ngày 14/11/2026 in giờ mở cửa 07:00 – 22:30. Quán có Wi-Fi, tên mạng in trên menu là "
            "'BIBLIO CAFE SACH'; mật khẩu không được lưu trong hệ thống — khách hỏi nhân viên tại quầy.",
            status="verified_branch", source_type="user_photo", url=None, retrieved_at=photo_at),
    ]
    pk = services["coworking_packages"]
    amen = [f["label"] for f in services["service_facts"] if f["scope"] == "coworking"]
    docs.append(doc(
        "doc-photo-coworking", "Gói co-working (bảng giá tại quán, 14/11/2026)", "coworking", "service", "src-photo-service-board",
        "Biblio 79 Ngụy Như Kon Tum có dịch vụ co-working. Bảng giá chụp tại quán ngày 14/11/2026 (giá đã gồm 10% VAT, chưa được quán "
        "xác nhận là hiện hành): " + "; ".join(f"gói {p['label']}: {fmt_vnd(p['price_vnd'])}" for p in pk) + ". Tiện ích đi kèm: "
        + "; ".join(amen) + ". Điều kiện áp dụng giảm 25% hóa đơn đồ uống và phạm vi 'decor theo sở thích' chưa được xác minh.",
        status="verified_branch", source_type="user_photo", url=None, retrieved_at=photo_at))
    room_lines = [f"{r['name']}: {r['area_m2']} m², {r['layout_note']}, {fmt_vnd(r['price_vnd'])}/ca {r['session_hours']} tiếng"
                  for r in services["meeting_rooms"]]
    fac = [f["label"] for f in services["service_facts"] if f["scope"] == "meeting_room" and f["kind"] == "amenity"]
    extras = []
    for f in services["service_facts"]:
        if f["kind"] != "extra_service":
            continue
        if f["price_from_vnd"] and f["price_to_vnd"]:
            extras.append(f"{f['label']} {fmt_vnd(f['price_from_vnd'])}–{fmt_vnd(f['price_to_vnd'])}")
        elif f["price_from_vnd"]:
            extras.append(f"{f['label']} từ {fmt_vnd(f['price_from_vnd'])}/{f['unit'] or 'lần'}")
        else:
            extras.append(f"{f['label']} (chưa rõ giá)")
    docs.append(doc(
        "doc-photo-meeting-rooms", "Thuê phòng hội thảo và không gian sự kiện (bảng giá tại quán, 14/11/2026)", "room_rental", "service",
        "src-photo-service-board",
        "Bảng giá chụp tại quán (giá theo ca 4 tiếng, đã gồm 10% VAT, chưa được quán xác nhận là hiện hành): " + "; ".join(room_lines)
        + ". Tiện ích chung: " + "; ".join(fac) + ". Dịch vụ thêm: " + "; ".join(extras)
        + ". Không có dữ liệu phòng trống — trợ lý không xác nhận hay nhận đặt phòng; khách liên hệ quán 0976 214 224.",
        status="verified_branch", source_type="user_photo", url=None, retrieved_at=photo_at))
    cat_lines = []
    for c in menu["categories"]:
        its = [i for i in menu["items"] if i["category_id"] == c["id"]]
        cat_lines.append(f"{c['name']} ({len(its)} món: {', '.join(i['name'] for i in its)})")
    lo = min(i["price_min_vnd"] for i in menu["items"])
    hi = max(i["price_max_vnd"] for i in menu["items"])
    docs.append(doc(
        "doc-photo-menu-overview", "Tổng quan menu đồ uống và đồ ăn (ảnh menu tại quán)", "food_beverage", "product", "src-photo-drink-menu",
        f"Menu chụp tại quán ngày 14/11/2026 có {len(menu['items'])} món trong {len(menu['categories'])} nhóm: " + "; ".join(cat_lines)
        + f". Giá niêm yết từ {fmt_vnd(lo)} đến {fmt_vnd(hi)}. Giá cụ thể, biến thể và tình trạng còn/hết phải tra trong menu "
        "(cơ sở dữ liệu), không lấy từ tài liệu này. Chưa có mô tả thành phần, độ ngọt hay caffeine được xác minh cho từng món.",
        status="verified_branch", source_type="user_photo", url=None, retrieved_at=photo_at,
        metadata={"food_source_id": "src-photo-food-menu"}))

    if gmaps:
        g_at = (gmaps_meta or {}).get("finished_at") or "2026-11-14T04:17:54.858Z"
        g_url = GMAPS_URL
        docs.append(doc(
            "doc-gmaps-location", "Google Maps: vị trí Biblio Book Cafe - 79 Ngụy Như Kon Tum", "location", "fact", "src-gmaps-listing",
            f"Listing Google Maps '{gmaps['title']}' (danh mục: {gmaps.get('categoryName')}) ghi địa chỉ: {gmaps['address']}. "
            f"Plus code: {gmaps.get('plusCode')}. Tọa độ: {gmaps['location']['lat']}, {gmaps['location']['lng']}. "
            f"Mức giá Google hiển thị: {gmaps.get('price')}. Listing không hiển thị giờ mở cửa và số điện thoại (truy xuất 14/11/2026).",
            status="verified_branch", source_type="google_maps", url=g_url, retrieved_at=g_at))
        attrs = []
        for group, values in (gmaps.get("additionalInfo") or {}).items():
            names = [k for v in values for k, ok in v.items() if ok]
            if names:
                attrs.append(f"{group}: {', '.join(names)}")
        docs.append(doc(
            "doc-gmaps-attributes", "Google Maps: tiện ích và đặc điểm (đỗ xe, trẻ em, làm việc, đặt chỗ)", "facilities", "fact",
            "src-gmaps-listing",
            "Thuộc tính trên listing Google Maps của chi nhánh (truy xuất 14/11/2026; do Google/cộng đồng tổng hợp, không phải thông báo "
            "của quán): " + "; ".join(attrs) + ".",
            status="verified_branch", source_type="google_maps", url=g_url, retrieved_at=g_at))
        dist = gmaps.get("reviewsDistribution") or {}
        docs.append(doc(
            "doc-gmaps-rating", "Google Maps: điểm đánh giá (ảnh chụp ngày 14/11/2026)", "customer_insights", "review", "src-gmaps-listing",
            f"Ngày 14/11/2026, listing Google Maps của Biblio 79 Ngụy Như Kon Tum có điểm {gmaps.get('totalScore')}/5 từ "
            f"{gmaps.get('reviewsCount')} đánh giá (5★: {dist.get('fiveStar')}, 4★: {dist.get('fourStar')}, 3★: {dist.get('threeStar')}, "
            f"2★: {dist.get('twoStar')}, 1★: {dist.get('oneStar')}). Điểm số thay đổi theo thời gian; khi nhắc phải kèm ngày truy xuất.",
            status="verified_branch", source_type="google_maps", url=g_url, retrieved_at=g_at))
        exclusions = curated.get("review_exclusions", {}).get("by_text_prefix", {})
        n = 0
        for r in gmaps.get("reviews") or []:
            text = normalize_text((r.get("text") or "").replace("<br>", " "))
            if not text or any(text.startswith(p) for p in exclusions):
                continue
            n += 1
            date = (r.get("publishedAtDate") or "")[:10]
            docs.append(doc(
                f"doc-gmaps-review-{n:02d}", f"Review Google Maps {r.get('stars')}★ ngày {date}", "customer_insights", "review",
                "src-gmaps-reviews", f"Nhận xét của một khách trên Google Maps ({r.get('stars')}★, đăng {date}): {text}",
                status="verified_branch", source_type="google_maps_review", url=r.get("reviewUrl") or g_url, retrieved_at=g_at,
                metadata={"stars": r.get("stars"), "published_at": date, "review_id": r.get("reviewId")}))

    decisions = curated["tiktok_decisions"]
    t_at = (tiktok_meta or {}).get("finished_at") or "2026-11-14T04:18:40.665Z"
    for v in tiktok:
        dec = decisions["accepted"].get(str(v.get("id")))
        if not dec or dec["status"] not in INGESTIBLE:
            continue
        date = (v.get("createTimeISO") or "")[:10]
        raw_caption = v.get("text") or ""
        repaired = "đ��" in raw_caption  # source text has a mangled 'đủ' ("đầy đủ tiện nghi")
        caption = normalize_text(re.sub(r"#\S+", "", raw_caption.replace("đ��", "đủ").replace("�", "")))
        docs.append(doc(
            f"doc-tiktok-{v['id']}", f"TikTok @{v.get('author_handle')} ({date})", dec["category"], "fact",
            "src-tiktok-bibliocafesach",
            f"Video TikTok của tài khoản @{v.get('author_handle')} (đăng {date}) — tài khoản tự giới thiệu là Biblio 79 Ngụy Như Kon Tum. "
            f"Nội dung chú thích: {caption}",
            status=dec["status"], source_type="tiktok", url=v.get("webVideoUrl"), retrieved_at=t_at,
            metadata={"published_at": date, "play_count": v.get("playCount"), "caption_repaired": repaired}))

    # Events summary (only branch-verified events go to the KB).
    events = [e for e in curated["events"] if e["verification_status"] in INGESTIBLE]
    lines = [f"{e['title']} — {e['start_date']} ({'đã diễn ra' if e['event_status'] == 'past' else e['event_status']}): {e['description']}"
             for e in events]
    docs.append(doc(
        "doc-events-overview", "Sự kiện tại Biblio 79 Ngụy Như Kon Tum: lịch sắp tới và sự kiện đã diễn ra", "events", "event",
        "src-kb-curation",
        "Tính đến 14/11/2026 chưa tìm thấy lịch sự kiện SẮP DIỄN RA nào được xác minh cho chi nhánh (fanpage Facebook không truy cập được). "
        "Trợ lý không được tự đưa ra sự kiện sắp tới. Các sự kiện đã diễn ra được nhắc trong nguồn công khai: " + " | ".join(lines),
        status="verified_branch", source_type="kb_curation", url=None, retrieved_at="2026-11-14T04:40:00.000Z",
        metadata={"citations": ["src-gmaps-reviews"], "event_ids": [e["id"] for e in events]}))

    for d in curated["documents"]:
        s = sources[d["source_id"]]
        docs.append(doc(d["id"], d["title"], d["category"], d["content_kind"], d["source_id"], d["content"],
                        status=s["verification_status"], source_type=s["source_type"], url=s["url"], retrieved_at=s["retrieved_at"],
                        branch_id=s["branch_id"] or BRANCH_ID, metadata=d.get("metadata")))
    for d in synthesis["documents"]:
        docs.append(doc(d["id"], d["title"], d["category"], d["content_kind"], "src-kb-curation", d["content"],
                        status=d.get("verification_status", "verified_branch"), source_type="kb_curation", url=None,
                        retrieved_at="2026-11-14T04:40:00.000Z",
                        branch_id=BRAND_ID if d.get("verification_status") == "brand_general" else BRANCH_ID,
                        metadata={"citations": d["citations"]}))
    for d in curated["rejected_documents"]:
        s = sources[d["source_id"]]
        docs.append(doc(d["id"], d["title"], d["category"], d["content_kind"], d["source_id"], d["content"],
                        status="rejected", source_type=s["source_type"], url=s["url"], retrieved_at=s["retrieved_at"],
                        branch_id=s["branch_id"], metadata=d.get("metadata")))
    return docs


def build_sources(curated: dict, gmaps_meta: dict | None, tiktok_meta: dict | None) -> list[dict]:
    sources = list(curated["sources"])
    if gmaps_meta:
        apify_meta = {"actor_id": gmaps_meta.get("actor_id"), "run_id": gmaps_meta.get("id"), "usage_total_usd": gmaps_meta.get("usage_total_usd"),
                      "charged_event_counts": gmaps_meta.get("charged_event_counts")}
        sources.append({"id": "src-gmaps-listing", "title": "Google Maps — Biblio Book Cafe - 79 Ngụy Như Kon Tum (listing)",
                        "source_type": "google_maps", "url": GMAPS_URL, "branch_id": BRANCH_ID, "verification_status": "verified_branch",
                        "retrieved_at": gmaps_meta.get("finished_at"), "published_at": None,
                        "notes": "Collected via Apify compass/crawler-google-places (1 place).", "metadata": apify_meta})
        sources.append({"id": "src-gmaps-reviews", "title": "Google Maps — đánh giá của khách (30 review liên quan nhất, không lưu thông tin cá nhân)",
                        "source_type": "google_maps_review", "url": GMAPS_URL, "branch_id": BRANCH_ID, "verification_status": "verified_branch",
                        "retrieved_at": gmaps_meta.get("finished_at"), "published_at": None,
                        "notes": "Reviews are customer opinions, not café facts. scrapeReviewsPersonalData=false.", "metadata": apify_meta})
    if tiktok_meta:
        sources.append({"id": "src-tiktok-bibliocafesach", "title": "TikTok — @bibliocafesach (tài khoản tự giới thiệu là Biblio 79 Ngụy Như Kon Tum)",
                        "source_type": "tiktok", "url": TIKTOK_ACCOUNT_URL, "branch_id": BRANCH_ID, "verification_status": "verified_branch",
                        "retrieved_at": tiktok_meta.get("finished_at"), "published_at": None,
                        "notes": "Found via Apify clockworks/tiktok-scraper search; caption of video 7646412336277982485 states address, hours and phone.",
                        "metadata": {"actor_id": tiktok_meta.get("actor_id"), "run_id": tiktok_meta.get("id"),
                                     "usage_total_usd": tiktok_meta.get("usage_total_usd"), "search_queries": tiktok_meta.get("input", {}).get("searchQueries")}})
    sources.append({"id": "src-user-bundle", "title": "biblio_cafe_kb_bundle (user-provided transcription of in-store photos)",
                    "source_type": "user_photo", "url": None, "branch_id": BRANCH_ID, "verification_status": "verified_branch",
                    "retrieved_at": "2026-11-14T03:23:00.000Z", "published_at": None,
                    "notes": "biblio_knowledge.md, biblio_menu.json, biblio_services.json — read-only originals.", "metadata": {}})
    return sorted(sources, key=lambda s: s["id"])


def build_social(tiktok: list[dict], curated: dict, gmaps: dict | None) -> dict:
    dec = curated["tiktok_decisions"]
    rows = []
    for v in tiktok:
        vid = str(v.get("id"))
        if vid in dec["accepted"]:
            status, reason = dec["accepted"][vid]["status"], dec["accepted"][vid]["note"]
            bucket = "accepted" if status in INGESTIBLE else "pending"
        elif vid in dec["pending"]:
            bucket, status, reason = "pending", "unverified_branch", dec["pending"][vid]
        else:
            bucket, status, reason = "rejected", "rejected", dec["rejected"].get(vid, "not reviewed")
        rows.append({"video_id": vid, "url": v.get("webVideoUrl"), "author_handle": v.get("author_handle"),
                     "published_at": (v.get("createTimeISO") or "")[:10], "play_count": v.get("playCount"),
                     "search_query": v.get("searchQuery"), "bucket": bucket, "verification_status": status, "reason": reason,
                     "caption": normalize_text(v.get("text") or "")[:300]})
    reviews = (gmaps or {}).get("reviews") or []
    return {
        "tiktok": {"collected": len(rows), "accepted": sum(r["bucket"] == "accepted" for r in rows),
                   "pending": sum(r["bucket"] == "pending" for r in rows), "rejected": sum(r["bucket"] == "rejected" for r in rows),
                   "videos": rows},
        "google_maps_reviews": {"collected": len(reviews),
                                "excluded_off_topic": len(curated.get("review_exclusions", {}).get("by_text_prefix", {})),
                                "stars": {str(s): sum(1 for r in reviews if r.get("stars") == s) for s in range(1, 6)},
                                "date_range": [min((r.get("publishedAtDate") or "")[:10] for r in reviews) if reviews else None,
                                               max((r.get("publishedAtDate") or "")[:10] for r in reviews) if reviews else None],
                                "personal_data": "not collected (scrapeReviewsPersonalData=false) and stripped on save"},
    }


UNVERIFIED = [
    ("availability", "Tình trạng còn/hết của toàn bộ 51 món (availability=unknown).", "src-user-bundle"),
    ("price_current", "Giá trên ảnh menu/bảng dịch vụ có còn hiện hành.", "src-user-bundle"),
    ("hot_cold", "Lựa chọn nóng/lạnh, đường, đá cho từng món.", "src-photo-drink-menu"),
    ("ingredients", "Thành phần, độ ngọt, caffeine, dị ứng của từng món.", "src-user-bundle"),
    ("yakult_cross", "Ý nghĩa dấu X viết tay cạnh 'Trà xoài Yakult'.", "src-photo-drink-menu"),
    ("name_bo_gia_dua_non", "Tên chính xác của món 'Bơ già dừa non'.", "src-photo-drink-menu"),
    ("name_chesse", "Chính tả 'chesse' trong 'Olong đào kem chesse', 'Matcha kem chesse'.", "src-photo-drink-menu"),
    ("tra_xuan_serving", "Tên và cách phục vụ 'Trà xuân 1/2 người'.", "src-photo-drink-menu"),
    ("room_availability", "Lịch trống phòng hội thảo; chính sách đặt cọc/hủy.", "src-photo-service-board"),
    ("cowork_discount", "Điều kiện giảm 25% hóa đơn đồ uống cho khách co-working (gói nào, cộng dồn?).", "src-photo-service-board"),
    ("cowork_decor", "Phạm vi 'Bố trí, decor theo sở thích'.", "src-photo-service-board"),
    ("backdrop_price", "Giá backdrop/standee.", "src-photo-service-board"),
    ("library_card", "Thẻ mượn sách: còn áp dụng? giá? (nguồn 2022).", "src-web-tadiha-2022"),
    ("parking_fee", "Phí gửi xe (Google Maps chỉ ghi 'có tính phí').", "src-gmaps-listing"),
    ("kids_area_current", "Khu trẻ em/khu tô tượng hiện còn hoạt động? giờ, phí?", "src-web-book365"),
    ("upcoming_events", "Lịch sự kiện sắp tới (fanpage không truy cập được).", "src-facebook-page"),
    ("email", "Email cafesachbiblio@gmail.com còn dùng? (nguồn 2022).", "src-web-tadiha-2022"),
    ("area_1000m2", "Diện tích 'hơn 1000m²' (bài tổng hợp, không ghi ngày).", "src-web-book365"),
    ("brand_history_dong_tay", "Quan hệ với 'Không gian văn hóa Đông Tây' / 'Cafe sách Đông Tây'.", "src-web-traveloka"),
    ("address_79a", "'79a Ngụy Như Kon Tum' trong video Civilis có phải chi nhánh này?", "src-tiktok-bibliocafesach"),
    ("wifi_password", "Mật khẩu Wi-Fi (có trên ảnh nhưng cố ý không lưu).", "src-photo-drink-menu"),
]


def render_markdown(profile: dict, menu: dict, services: dict, docs: list[dict], sources: list[dict], social: dict, events: list[dict]) -> str:
    out = ["# Biblio 79 Ngụy Như Kon Tum — Knowledge Base mở rộng", "",
           "> Sinh tự động bởi `scripts/knowledge/normalize.py` — KHÔNG sửa tay. Nguồn gốc: ảnh tại quán (user-provided), Google Maps, "
           "TikTok @bibliocafesach, bài viết công khai. Không có dữ liệu nào được chủ quán xác nhận (`owner_verified` = 0).", "",
           "## 1. Hồ sơ cơ sở", "",
           f"- Tên: {profile['display_name']}",
           f"- Địa chỉ: {profile['address']['value']} (nguồn: {', '.join(profile['address']['sources'])})",
           f"- Tọa độ: {profile['location']['latitude']}, {profile['location']['longitude']} — Plus code {profile['location']['plus_code']}",
           f"- Điện thoại: {profile['phone']['value']} (mâu thuẫn cũ: {profile['phone']['conflicts'][0]['value']} — 2022)",
           f"- Giờ mở cửa: {profile['opening_hours']['open']}–{profile['opening_hours']['close']} {profile['opening_hours']['days']}",
           f"- Facebook: {profile['channels']['facebook']['url']} · TikTok: {profile['channels']['tiktok']['url']} · Website: chưa tìm thấy",
           f"- Google Maps (14/11/2026): {profile['google_maps_snapshot']['rating']}/5 · {profile['google_maps_snapshot']['reviews_count']} đánh giá"
           if profile.get("google_maps_snapshot") else "- Google Maps: chưa thu thập", "",
           "## 2. Menu (giá niêm yết trên ảnh, chưa xác nhận; tình trạng: chưa xác nhận)", ""]
    for c in menu["categories"]:
        out.append(f"### {c['name']}")
        out.append("| ID | Món | Giá (VNĐ) | Tags suy luận |")
        out.append("|---|---|---:|---|")
        for i in (x for x in menu["items"] if x["category_id"] == c["id"]):
            price = " / ".join(f"{v['label']} {v['price_vnd']:,}" for v in i["variants"]) if i["variants"] else f"{i['base_price_vnd']:,}"
            out.append(f"| {i['id']} | {i['name']} | {price} | {', '.join(i['suggested_tags'])} |")
        out.append("")
    out += ["## 3. Co-working", "", "| Gói | Giá |", "|---|---:|"]
    out += [f"| {p['label']} | {p['price_vnd']:,} |" for p in services["coworking_packages"]]
    out += ["", "## 4. Phòng hội thảo (ca 4 tiếng, gồm VAT)", "", "| Phòng | m² | Sức chứa | Giá |", "|---|---:|---|---:|"]
    out += [f"| {r['name']} | {r['area_m2']} | {r['layout_note']} | {r['price_vnd']:,} |" for r in services["meeting_rooms"]]
    out += ["", "## 5. Sự kiện", ""]
    out += [f"- [{e['event_status']}] {e['start_date']} — {e['title']} ({e['verification_status']}) — {e['source_url']}" for e in events]
    out += ["- Không có sự kiện sắp tới đã xác minh (14/11/2026).", "",
            f"## 6. Mạng xã hội\n\nTikTok: {social['tiktok']['collected']} video thu thập — {social['tiktok']['accepted']} nhận, "
            f"{social['tiktok']['pending']} chờ xác minh, {social['tiktok']['rejected']} loại. Google Maps: {social['google_maps_reviews']['collected']} review.", "",
            "## 7. Tài liệu tri thức (được index)", ""]
    for d in docs:
        if d["verification_status"] in INGESTIBLE:
            out.append(f"- `{d['id']}` [{d['category']}/{d['content_kind']}/{d['verification_status']}] {d['title']}")
    out += ["", "## 8. Nguồn", ""]
    out += [f"- `{s['id']}` [{s['verification_status']}] {s['title']} — {s['url'] or '(local)'}" for s in sources]
    return "\n".join(out) + "\n"


def main() -> None:
    bundle_menu = read_json(BUNDLE_DIR / "biblio_menu.json")
    bundle_services = read_json(BUNDLE_DIR / "biblio_services.json")
    curated = read_json(CURATED_DIR / "external_knowledge.json")
    synthesis = read_json(CURATED_DIR / "synthesis_documents.json")

    gmaps_path, tiktok_path = RAW_APIFY_DIR / "google-maps" / "items.json", RAW_APIFY_DIR / "tiktok" / "items.json"
    gmaps = read_json(gmaps_path)[0] if gmaps_path.exists() else None
    gmaps_meta = read_json(RAW_APIFY_DIR / "google-maps" / "run_meta.json") if gmaps_path.exists() else None
    tiktok = read_json(tiktok_path) if tiktok_path.exists() else []
    tiktok_meta = read_json(RAW_APIFY_DIR / "tiktok" / "run_meta.json") if tiktok_path.exists() else None
    if gmaps is None or not tiktok:
        print("WARNING: Apify raw data missing; normalized output will lack Google Maps/TikTok documents.")

    menu = build_menu(bundle_menu)
    services = build_services(bundle_services)
    profile = build_profile(gmaps, bundle_services)
    sources = build_sources(curated, gmaps_meta, tiktok_meta)
    source_map = {s["id"]: s for s in sources}
    docs = build_documents(menu, services, gmaps, gmaps_meta, tiktok, tiktok_meta, curated, synthesis, source_map)
    social = build_social(tiktok, curated, gmaps)
    events = curated["events"]

    missing = {d["source_id"] for d in docs} - set(source_map)
    if missing:
        raise SystemExit(f"Documents reference unknown sources: {missing}")
    hashes = [d["content_hash"] for d in docs]
    if len(hashes) != len(set(hashes)):
        raise SystemExit("Duplicate document content detected")

    write_json(NORMALIZED_DIR / "cafe_profile.json", profile)
    write_json(NORMALIZED_DIR / "menu.json", menu)
    write_json(NORMALIZED_DIR / "services.json", services)
    write_jsonl(NORMALIZED_DIR / "documents.jsonl", docs)
    write_json(NORMALIZED_DIR / "source_manifest.json", {"branch_id": BRANCH_ID, "sources": sources})
    write_json(NORMALIZED_DIR / "events.json", {"branch_id": BRANCH_ID, "as_of": "2026-11-14", "upcoming_verified": 0, "events": events})
    write_json(NORMALIZED_DIR / "social_insights.json", social)
    write_json(NORMALIZED_DIR / "unverified_claims.json",
               [{"id": k, "claim": c, "source_id": s, "status": "pending_owner_confirmation"} for k, c, s in UNVERIFIED])
    (KNOWLEDGE_DIR / "knowledge_extended.md").write_text(
        render_markdown(profile, menu, services, docs, sources, social, events), encoding="utf-8", newline="\n")

    ing = sum(d["verification_status"] in INGESTIBLE for d in docs)
    print(f"menu items={len(menu['items'])} categories={len(menu['categories'])} variants={sum(len(i['variants']) for i in menu['items'])}")
    print(f"coworking={len(services['coworking_packages'])} rooms={len(services['meeting_rooms'])} service_facts={len(services['service_facts'])}")
    print(f"documents total={len(docs)} ingestible={ing} rejected={sum(d['verification_status'] == 'rejected' for d in docs)}")
    print(f"sources={len(sources)} events={len(events)} tiktok={social['tiktok']['accepted']}/{social['tiktok']['pending']}/{social['tiktok']['rejected']}")


if __name__ == "__main__":
    main()
