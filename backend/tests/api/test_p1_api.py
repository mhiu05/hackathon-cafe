import json

from agents import SQLiteSession

from app.orders.service import LineInput, create_draft


def test_insights_counts_orders_and_tool_calls(client, conn):
    body = {"lines": [{"item_id": "menu_030", "quantity": 2}], "expected_total_vnd": 90000}
    client.post("/api/orders", headers={"Idempotency-Key": "insights-order-1"}, json=body)
    client.post("/api/orders", headers={"Idempotency-Key": "insights-order-2"}, json=body)
    token = client.post("/api/admin/login", json={"pin": "246810"}).json()["token"]
    h = {"Authorization": "Bearer " + token}
    for old, new in [("pending", "confirmed"), ("confirmed", "ready"), ("ready", "completed")]:
        assert client.patch("/api/admin/orders/1/status", headers=h, json={"to_status": new, "expected_status": old}).status_code == 200
    conn.execute("INSERT INTO agent_runs(id,conversation_id,status,model,input_tokens,output_tokens,user_message_chars,started_at) VALUES ('run','abc','completed','gpt-6-luna',123,45,2,'2026-11-14T00:00:00.000Z')")
    conn.execute("INSERT INTO agent_tool_calls(run_id,call_id,tool,ok,error_code,latency_ms,created_at) VALUES ('run','call','search_menu',1,NULL,10,'2026-11-14T00:00:00.000Z')")
    conn.execute("INSERT INTO agent_tool_calls(run_id,call_id,tool,ok,error_code,latency_ms,created_at) VALUES ('run','call2','prepare_order',0,'ITEM_UNAVAILABLE',10,'2026-11-14T00:00:00.000Z')")
    r = client.get("/api/admin/insights", headers=h)
    assert r.status_code == 200
    got = r.json()
    assert got["orders_total"] == 2 and got["orders_by_status"]["completed"] == 1 and got["orders_by_status"]["pending"] == 1
    assert got["revenue_completed_vnd"] == 90000
    assert got["top_items"] == [{"item_id": "menu_030", "name": "Matcha latte", "quantity": 4}]
    assert got["agent"] == {"runs": 1, "tool_calls": {"search_menu": 1, "prepare_order": 1}, "tool_errors": 1, "input_tokens": 123, "output_tokens": 45}
    assert client.get("/api/admin/insights").status_code == 401


async def test_draft_confirm_appends_one_memory_note(client, conn, settings):
    conversation = "a" * 32
    d = create_draft(conn, conversation_id=conversation, lines=[LineInput("menu_024", None, 1)], customer_name=None, table_label=None, note=None)
    url = "/api/orders/drafts/" + d["draft_id"] + "/confirm"
    assert client.post(url, json={"expected_total_vnd": 45000}).status_code == 201
    assert client.post(url, json={"expected_total_vnd": 45000}).status_code == 200
    session = SQLiteSession("chat-" + conversation, settings.agent_sessions_db_path)
    messages = await session.get_items()
    session.close()
    assert messages == [{"role": "assistant", "content": "Đơn BB-0001 đã được tạo từ đơn nháp (45000) và đang chờ quán xác nhận."}]


async def test_agent_history_only_text_and_scoped_by_conversation(client, settings):
    conversation = "b" * 32
    session = SQLiteSession("chat-" + conversation, settings.agent_sessions_db_path)
    await session.add_items([
        {"role": "user", "content": "Menu?"},
        {"type": "function_call", "name": "search_menu", "call_id": "c", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "c", "output": json.dumps({"ok": True, "secret_internal": "not history"})},
        {"role": "assistant", "type": "message", "content": [{"type": "output_text", "text": "Matcha latte 45.000đ", "annotations": []}]},
    ])
    session.close()
    r = client.get("/api/agent/history", headers={"X-Conversation-Id": conversation})
    assert r.status_code == 200
    assert r.json() == {"messages": [{"role": "user", "text": "Menu?"}, {"role": "assistant", "text": "Matcha latte 45.000đ"}]}
    assert client.get("/api/agent/history", headers={"X-Conversation-Id": "c" * 32}).json() == {"messages": []}
    assert client.get("/api/agent/history").status_code == 400
