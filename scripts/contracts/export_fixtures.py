"""Generate contract fixtures for the public catalog endpoints from data/cafe.db.

    uv run python scripts/contracts/export_fixtures.py

Writes contracts/fixtures/{cafe,menu,services}.json using app.catalog.dto (the same builders the API uses),
so backend contract tests and the frontend mock client share one shape. `is_open_now` is pinned to false in the fixture;
contract tests ignore that field.
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.catalog.dto import cafe_profile_dto, menu_response_dto, services_response_dto  # noqa: E402
from app.db.connection import connect  # noqa: E402
from app.settings import load_settings  # noqa: E402

OUT = REPO_ROOT / "contracts" / "fixtures"


def dump(name: str, payload: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    settings = load_settings()
    conn = connect(settings.database_path, read_only=True)
    try:
        cafe = cafe_profile_dto(conn, datetime(2026, 11, 14, tzinfo=UTC))
        cafe["is_open_now"] = False
        dump("cafe.json", cafe)
        dump("menu.json", menu_response_dto(conn))
        dump("services.json", services_response_dto(conn))
    finally:
        conn.close()
    print("wrote", sorted(p.name for p in OUT.glob("*.json")))


if __name__ == "__main__":
    main()
