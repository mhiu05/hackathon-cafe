# test_agent_stream.py
import openai, pytest
from agents import SQLiteSession
from agents.testing import ScriptedModel, ModelStep, assistant_message, function_call
from app.agent.factory import build_agent
from app.agent.stream import AgentDeps, run_chat_stream
from app.knowledge.retrieval import KnowledgeIndex
from .helpers import collect
CONV = "a" * 32

def deps_for(settings, conn, steps):
    return AgentDeps(settings=settings, agent=build_agent(settings, model=ScriptedModel(steps)),
                     index=KnowledgeIndex.load(conn), embedder=None)

async def run(deps, message, tmp_path):
    return await collect(run_chat_stream(deps, CONV, message, session=SQLiteSession("t", tmp_path / "s.db")))

async def test_menu_question_streams_tool_then_text(settings, conn, tmp_path):
    deps = deps_for(settings, conn, [[function_call("search_menu", {"query": "matcha"}, call_id="c1")],
                                     [assistant_message("Có 5 món matcha.")]])
    ev = await run(deps, "Menu matcha có gì?", tmp_path)
    states = [d["state"] for n, d in ev if n == "agent_state"]
    assert [n for n, _ in ev][0] == "run_started" and ev[-1][0] == "done" and ev[-1][1]["reason"] == "completed"
    assert states == ["thinking", "searching", "thinking", "composing", "idle"]
    assert next(d for n, d in ev if n == "tool_finished") == {"call_id": "c1", "tool": "search_menu", "ok": True, "summary": "5 món"}

async def test_prepare_order_emits_draft_and_creates_no_order(settings, conn, tmp_path):
    args = {"lines": [{"item_id": "menu_024", "variant_id": None, "quantity": 1, "note": None}],
            "customer_name": None, "table_label": None, "note": None}
    deps = deps_for(settings, conn, [[function_call("prepare_order", args, call_id="c2")],
                                     [assistant_message("Bạn bấm Xác nhận đặt món nhé.")]])
    ev = await run(deps, "Lấy 1 trà chanh gừng mật ong", tmp_path)
    draft = next(d["draft"] for n, d in ev if n == "order_draft")
    assert draft["quote"]["total_vnd"] == 45000 and draft["status"] == "open"
    assert "working" in [d["state"] for n, d in ev if n == "agent_state"]
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0

async def test_prepare_order_unknown_item_returns_tool_error(settings, conn, tmp_path):
    args = {"lines": [{"item_id": "menu_999", "variant_id": None, "quantity": 1, "note": None}],
            "customer_name": None, "table_label": None, "note": None}
    deps = deps_for(settings, conn, [[function_call("prepare_order", args, call_id="c3")], [assistant_message("Món không có.")]])
    ev = await run(deps, "Lấy món 999", tmp_path)
    assert next(d for n, d in ev if n == "tool_finished")["ok"] is False and not [1 for n, _ in ev if n == "order_draft"]

async def test_model_error_emits_model_unavailable(settings, conn, tmp_path):
    err = openai.APIConnectionError(request=__import__("httpx").Request("POST", "https://api.openai.com/v1/responses"))
    deps = deps_for(settings, conn, [ModelStep.raise_error(err)])
    ev = await run(deps, "Xin chào", tmp_path)
    assert ("error", {"code": "MODEL_UNAVAILABLE", "message": "Trợ lý tạm thời không khả dụng — bạn vẫn có thể đặt món từ Menu.", "retryable": True}) in ev
    assert ev[-1][0] == "done" and ev[-1][1]["reason"] == "error"


async def test_prepare_order_sold_out_rejected(settings, conn, tmp_path):
    conn.execute("UPDATE menu_items SET availability='sold_out' WHERE id='menu_019'")
    args = {"lines": [{"item_id": "menu_019", "variant_id": None, "quantity": 1, "note": None}]}
    deps = deps_for(settings, conn, [[function_call("prepare_order", args, call_id="sold")], [assistant_message("M?n ?? h?t.")]])
    ev = await run(deps, "L?y tr? xo?i Yakult", tmp_path)
    assert next(d for n, d in ev if n == "tool_finished")["ok"] is False
    assert not [d for n, d in ev if n == "order_draft"]
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0


async def test_get_order_status_scoped_to_conversation(settings, conn, tmp_path):
    import json
    from app.orders.service import create_order, LineInput
    for i, conversation in enumerate([CONV, "b" * 32]):
        create_order(conn, lines=[LineInput("menu_030", None, 1)], expected_total_vnd=45000, customer_name=None,
                     table_label=None, note=None, source="ui", idempotency_key="scope-key-" + str(i), conversation_id=conversation)
    def check(call):
        outputs = [x for x in call.input if x.get("type") == "function_call_output"]
        data = json.loads(outputs[-1]["output"])
        assert [o["code"] for o in data["orders"]] == ["BB-0001"]
        assert data["orders"][0]["total_vnd"] == 45000
        return [assistant_message("??n BB-0001 ?ang ch? qu?n x?c nh?n.")]
    deps = deps_for(settings, conn, [[function_call("get_order_status", {}, call_id="status")], ModelStep.respond(check)])
    ev = await run(deps, "??n m?nh sao r?i?", tmp_path)
    assert ev[-1][1]["reason"] == "completed"


async def test_knowledge_sources_and_tool_calls_logged(settings, conn, tmp_path):
    steps = [[function_call("get_cafe_info", {"topic": "wifi"}, call_id="info"),
              function_call("search_cafe_knowledge", {"query": "gui xe", "category": "faq"}, call_id="kb")],
             [function_call("recommend_drinks", {"preferences": ["tra"], "max_price_vnd": 50000}, call_id="rec"),
              function_call("get_coworking_info", {"topic": "rooms", "min_capacity": 20}, call_id="room")],
             [assistant_message("Vui l?ng h?i nh?n vi?n m?t kh?u Wi-Fi.")]]
    deps = deps_for(settings, conn, steps)
    ev = await run(deps, "Wi-Fi, g?i xe, tr? d??i 50k v? ph?ng 20 ng??i?", tmp_path)
    assert ev[-1][1]["reason"] == "completed"
    sources = next(d["sources"] for n, d in ev if n == "message_completed")
    assert sources and len({s["source_id"] for s in sources}) == len(sources)
    assert all({"title", "url", "retrieved_at", "verification_status"} <= s.keys() for s in sources)
    assert conn.execute("SELECT COUNT(*) FROM agent_tool_calls WHERE ok=1").fetchone()[0] == 4
    assert conn.execute("SELECT status FROM agent_runs").fetchone()[0] == "completed"


async def test_agent_session_retains_text_across_turns(settings, conn, tmp_path):
    session = SQLiteSession("memory", tmp_path / "memory.db")
    deps = deps_for(settings, conn, [[assistant_message("Xin ch?o Minh.")]])
    await collect(run_chat_stream(deps, CONV, "M?nh l? Minh", session=session))
    def check(call):
        assert any(x.get("role") == "user" and x.get("content") == "M?nh l? Minh" for x in call.input)
        return [assistant_message("Minh nh?.")]
    deps = deps_for(settings, conn, [ModelStep.respond(check)])
    ev = await collect(run_chat_stream(deps, CONV, "T?n m?nh?", session=session))
    assert ev[-1][1]["reason"] == "completed"
    session.close()


def test_full_agent_draft_rest_admin_status_loop(client, conn, settings):
    import json
    from .helpers import parse_sse
    h = {"X-Conversation-Id": CONV}
    client.app.state.agent = build_agent(settings, model=ScriptedModel([
        [function_call("search_menu", {"query": "tra chanh gung"}, call_id="menu")],
        [function_call("prepare_order", {"lines": [{"item_id": "menu_024", "quantity": 1}]}, call_id="draft")],
        [assistant_message("B?n ki?m tra v? b?m X?c nh?n ??t m?n nh?.")]]))
    response = client.post("/api/agent/chat/stream", headers=h, json={"message": "L?y m?t tr? chanh g?ng m?t ong"})
    assert response.status_code == 200
    ev = parse_sse([response.text])
    d = next(data["draft"] for n, data in ev if n == "order_draft")
    assert d["quote"]["total_vnd"] == 45000
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
    url = "/api/orders/drafts/" + d["draft_id"] + "/confirm"
    assert client.post(url, json={"expected_total_vnd": 45000}).status_code == 201
    assert client.post(url, json={"expected_total_vnd": 45000}).status_code == 200
    token = client.post("/api/admin/login", json={"pin": "246810"}).json()["token"]
    auth = {"Authorization": "Bearer " + token}
    assert client.patch("/api/admin/orders/1/status", headers=auth, json={"to_status": "confirmed", "expected_status": "pending"}).status_code == 200
    def check(call):
        outputs = [x for x in call.input if x.get("type") == "function_call_output"]
        order = json.loads(outputs[-1]["output"])["orders"][0]
        assert order["code"] == "BB-0001" and order["status"] == "confirmed" and order["total_vnd"] == 45000
        return [assistant_message("??n BB-0001 ?? ???c qu?n nh?n.")]
    client.app.state.agent = build_agent(settings, model=ScriptedModel([
        [function_call("get_order_status", {}, call_id="status")], ModelStep.respond(check)]))
    ev = parse_sse([client.post("/api/agent/chat/stream", headers=h, json={"message": "??n m?nh sao r?i?"}).text])
    assert ev[-1][1]["reason"] == "completed"
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1
