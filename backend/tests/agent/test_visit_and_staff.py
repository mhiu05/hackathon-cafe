# test_visit_and_staff.py — plan_visit, request_staff, staff board API, in-stock default.
from datetime import datetime, timezone

import pytest
from agents import SQLiteSession
from agents.testing import ScriptedModel, assistant_message, function_call

from app.agent.factory import build_agent
from app.agent.instructions import INSTRUCTIONS
from app.agent.stream import AgentDeps, run_chat_stream
from app.agent.tools import ALL_TOOLS
from app.catalog.planning import plan_visit
from app.knowledge.retrieval import KnowledgeIndex
from app.realtime.bus import EventBus
from app.staff.service import MAX_OPEN_PER_CONVERSATION, create_request
from .helpers import collect

CONV = "b" * 32
NOW = datetime(2026, 11, 14, 2, 0, tzinfo=timezone.utc)  # 09:00 in Hà Nội


def plan(conn, **kw):
    args = {"hours": 3, "people": 1, "budget_per_person_vnd": None, "start_time": "09:00", "needs": []} | kw
    return plan_visit(conn, now=NOW, **args)


def test_menu_defaults_to_in_stock(conn):
    assert conn.execute("SELECT COUNT(*) FROM menu_items WHERE availability!='available'").fetchone()[0] == 0
    assert "chưa xác nhận còn hàng" not in INSTRUCTIONS


def test_solo_plan_compares_common_area_and_coworking_without_rooms(conn):
    p = plan(conn)
    kinds = [o["kind"] for o in p["options"]]
    assert kinds[0] == "common_area" and "coworking_day" in kinds and "meeting_room" not in kinds
    cowork = next(o for o in p["options"] if o["kind"] == "coworking_day")
    assert cowork["per_person_vnd"] == 55000 and cowork["total_vnd"] == 55000
    common = p["options"][0]
    assert common["per_person_vnd"] == common["cheapest_drinks"][0]["price_min_vnd"] <= 55000
    assert p["timing"] == {"start": "09:00", "end": "12:00", "open": "07:00", "close": "22:30", "fits_opening_hours": True}


def test_plan_warns_when_session_runs_past_closing(conn):
    t = plan(conn, start_time="21:00")["timing"]
    assert t["fits_opening_hours"] is False and t["max_hours_from_start"] == 1.5 and "22:30" in t["warning"]


def test_plan_before_opening_and_default_start_uses_local_now(conn):
    assert "07:00" in plan(conn, start_time="06:00")["timing"]["warning"]
    assert plan(conn, start_time=None)["timing"]["start"] == "09:00"


def test_group_with_projector_puts_rooms_first_and_prices_sessions(conn):
    p = plan(conn, hours=5, people=12, needs=["projector"])
    first = p["options"][0]
    assert first["kind"] == "meeting_room" and first["room_id"] == "room-4"
    assert first["sessions"] == 2 and first["total_vnd"] == 2 * 770000 and first["per_person_vnd"] == -(-1540000 // 12)
    assert "máy chiếu" in first["needs_met"]
    common = next(o for o in p["options"] if o["kind"] == "common_area")
    assert common["needs_unverified"] == ["máy chiếu"] and p["options"].index(common) > p["options"].index(first)


def test_fixed_seat_need_excludes_common_area_from_top(conn):
    p = plan(conn, needs=["fixed_seat", "power_outlet"], budget_per_person_vnd=60000)
    assert p["options"][0]["kind"] == "coworking_day" and p["options"][0]["within_budget"] is True
    common = next(o for o in p["options"] if o["kind"] == "common_area")
    assert common["needs_unmet"] == ["chỗ ngồi cố định"] and common["needs_unverified"] == ["ổ cắm điện"]


def test_staff_request_limit_per_conversation(conn):
    for _ in range(MAX_OPEN_PER_CONVERSATION):
        create_request(conn, conversation_id=CONV, kind="water", table_label=None, note=None)
    with pytest.raises(Exception) as e:
        create_request(conn, conversation_id=CONV, kind="water", table_label=None, note=None)
    assert e.value.code == "STAFF_REQUEST_LIMIT"


def test_new_tools_registered_with_labels():
    from app.agent.stream import TOOL_LABELS
    names = {t.name for t in ALL_TOOLS}
    assert {"plan_visit", "request_staff"} <= names and names <= set(TOOL_LABELS)


async def test_request_staff_tool_creates_row_and_notifies_admin(settings, conn, tmp_path):
    bus = EventBus()
    model = ScriptedModel([[function_call("request_staff", {"kind": "wifi", "table_label": "Bàn 5", "note": "Wi-Fi yếu"}, call_id="s1")],
                           [assistant_message("Mình đã báo nhân viên (YC-0001).")]])
    deps = AgentDeps(settings=settings, agent=build_agent(settings, model=model), index=KnowledgeIndex.load(conn), embedder=None, bus=bus)
    async with bus.subscribe("admin") as events:
        ev = await collect(run_chat_stream(deps, CONV, "Báo nhân viên giúp mình", session=SQLiteSession("t", tmp_path / "s.db")))
        name, data = await events.__anext__()
    assert next(d for n, d in ev if n == "tool_finished") == {"call_id": "s1", "tool": "request_staff", "ok": True,
                                                            "summary": "Đã báo nhân viên (YC-0001)"}
    assert "working" in [d["state"] for n, d in ev if n == "agent_state"]
    assert name == "staff_request_created" and data["request"]["kind_label"] == "Wi-Fi / mạng"
    row = conn.execute("SELECT conversation_id,kind,table_label,status FROM staff_requests").fetchone()
    assert tuple(row) == (CONV, "wifi", "Bàn 5", "open")


async def test_plan_visit_tool_streams_summary(settings, conn, tmp_path):
    model = ScriptedModel([[function_call("plan_visit", {"hours": 4, "people": 2}, call_id="p1")], [assistant_message("Có 2 phương án.")]])
    deps = AgentDeps(settings=settings, agent=build_agent(settings, model=model), index=KnowledgeIndex.load(conn), embedder=None)
    ev = await collect(run_chat_stream(deps, CONV, "Hai đứa học 4 tiếng", session=SQLiteSession("t", tmp_path / "s.db")))
    assert next(d for n, d in ev if n == "tool_finished")["summary"] == "2 phương án"


def test_admin_lists_and_resolves_staff_requests(client, conn):
    create_request(conn, conversation_id=CONV, kind="clean_table", table_label="Bàn 2", note=None)
    assert client.get("/api/admin/staff-requests").status_code == 401
    h = {"Authorization": "Bearer " + client.post("/api/admin/login", json={"pin": "246810"}).json()["token"]}
    listing = client.get("/api/admin/staff-requests?status=open", headers=h).json()["requests"]
    assert [(r["code"], r["kind_label"], r["status"]) for r in listing] == [("YC-0001", "Dọn bàn", "open")]
    r = client.patch(f"/api/admin/staff-requests/{listing[0]['id']}", headers=h, json={"status": "done"})
    assert r.status_code == 200 and r.json()["status"] == "done" and r.json()["resolved_at"]
    assert client.patch(f"/api/admin/staff-requests/{listing[0]['id']}", headers=h, json={"status": "done"}).status_code == 200
    assert client.get("/api/admin/staff-requests?status=open", headers=h).json()["requests"] == []
    assert client.patch("/api/admin/staff-requests/999", headers=h, json={"status": "done"}).status_code == 404
