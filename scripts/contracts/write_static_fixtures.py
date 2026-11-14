"""Write hand-authored contract fixtures (orders, drafts, admin list, agent SSE transcript).

    uv run python scripts/contracts/write_static_fixtures.py contracts/fixtures

Requires contracts/fixtures/quote.json (static). Edit values here, never the JSON by hand.
"""
import json
import pathlib
import sys

out = pathlib.Path(sys.argv[1])

quote_ui = json.loads((out / "quote.json").read_text(encoding="utf-8"))
W_PR = "Giá theo menu chụp ngày 14/11/2026, chờ quán xác nhận."


def order_line(q):
    return {k: v for k, v in q.items() if k != "availability"}


order_ui = {
    "id": 1, "code": "BB-0001", "status": "pending", "status_label": "Chờ quán xác nhận", "source": "ui",
    "customer_name": "Minh", "table_label": "Bàn 12", "note": None, "lines": [order_line(l) for l in quote_ui["lines"]],
    "subtotal_vnd": 115000, "total_vnd": 115000, "item_count": 3, "status_reason": None,
    "created_at": "2026-11-14T09:00:05.120Z", "updated_at": "2026-11-14T09:00:05.120Z",
    "events": [{"from_status": None, "to_status": "pending", "actor": "customer", "note": None, "created_at": "2026-11-14T09:00:05.120Z"}],
}
draft_quote = {
    "lines": [{"line_no": 1, "item_id": "menu_024", "variant_id": None, "item_name": "Trà chanh gừng mật ong", "variant_label": None,
               "unit_price_vnd": 45000, "quantity": 1, "line_total_vnd": 45000, "availability": "available", "note": None}],
    "subtotal_vnd": 45000, "total_vnd": 45000, "item_count": 1, "currency": "VND",
    "warnings": [{"code": "PRICE_UNVERIFIED", "message": W_PR, "item_ids": ["menu_024"]}],
    "quoted_at": "2026-11-14T09:05:00.000Z",
}
draft = {"draft_id": "3c9e51a07d2b4f6e8a1c9d0b2e4f6a8c", "status": "open", "quote": draft_quote, "customer_name": None,
         "table_label": None, "note": None, "order_code": None, "created_at": "2026-11-14T09:05:00.000Z",
         "expires_at": "2026-11-14T09:35:00.000Z"}
order_draft = {
    "id": 2, "code": "BB-0002", "status": "pending", "status_label": "Chờ quán xác nhận", "source": "agent_draft",
    "customer_name": None, "table_label": None, "note": None, "lines": [order_line(l) for l in draft_quote["lines"]],
    "subtotal_vnd": 45000, "total_vnd": 45000, "item_count": 1, "status_reason": None,
    "created_at": "2026-11-14T09:05:20.000Z", "updated_at": "2026-11-14T09:05:20.000Z",
    "events": [{"from_status": None, "to_status": "pending", "actor": "customer", "note": "Xác nhận từ đơn nháp", "created_at": "2026-11-14T09:05:20.000Z"}],
}
confirmed = dict(order_ui, status="confirmed", status_label="Quán đã nhận đơn", updated_at="2026-11-14T09:02:00.000Z",
                 events=order_ui["events"] + [{"from_status": "pending", "to_status": "confirmed", "actor": "admin", "note": None,
                                                "created_at": "2026-11-14T09:02:00.000Z"}],
                 allowed_next=["preparing", "ready", "cancelled"])
admin_list = {"orders": [dict(order_draft, allowed_next=["confirmed", "rejected", "cancelled"]), confirmed],
              "counts": {"pending": 1, "confirmed": 1, "preparing": 0, "ready": 0, "completed": 0, "rejected": 0, "cancelled": 0}}

for name, payload in [("order.json", order_ui), ("draft.json", draft), ("order_from_draft.json", order_draft),
                      ("admin_orders.json", admin_list)]:
    (out / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def ev(name, data):
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


usage = lambda i, o, r: {"input_tokens": i, "output_tokens": o, "requests": r}  # noqa: E731
t1_text = ("Mình chưa có thông tin độ ngọt đã xác minh, nhưng theo tên món bạn có thể thử:\n"
           "- Trà chanh gừng mật ong — 45.000đ\n- Trà thạch đào — 45.000đ\n- Chanh leo (nước ép) — 40.000đ\nBạn muốn đặt món nào?")
t2_text = ("Mình đã chuẩn bị đơn nháp: 1 Trà chanh gừng mật ong — 45.000đ. Bạn kiểm tra rồi bấm \"Xác nhận đặt món\" trên thẻ "
           "để gửi đơn tới quầy nhé (thanh toán tại quầy).")
t3_text = "Đơn BB-0002 đang ở trạng thái: Quán đã nhận đơn."
turn1 = "".join([
    ev("run_started", {"run_id": "7f0c2a8e1b3d4c5f9a0b1c2d3e4f5a6b"}),
    ev("agent_state", {"state": "thinking"}),
    ev("tool_started", {"call_id": "call_1", "tool": "recommend_drinks", "label": "Đang tìm món hợp ý bạn"}),
    ev("agent_state", {"state": "searching"}),
    ev("tool_finished", {"call_id": "call_1", "tool": "recommend_drinks", "ok": True, "summary": "3 gợi ý"}),
    ev("agent_state", {"state": "thinking"}),
    ev("agent_state", {"state": "composing"}),
    ev("text_delta", {"delta": t1_text[:70]}),
    ev("text_delta", {"delta": t1_text[70:]}),
    ev("message_completed", {"text": t1_text, "sources": []}),
    ev("agent_state", {"state": "idle"}),
    ev("done", {"reason": "completed", "usage": usage(1840, 96, 2)}),
])
turn2 = "".join([
    ev("run_started", {"run_id": "9b11d0c4e5f6a7b8c9d0e1f2a3b4c5d6"}),
    ev("agent_state", {"state": "thinking"}),
    ev("tool_started", {"call_id": "call_2", "tool": "prepare_order", "label": "Chuẩn bị đơn nháp"}),
    ev("agent_state", {"state": "working"}),
    ev("tool_finished", {"call_id": "call_2", "tool": "prepare_order", "ok": True, "summary": "Đơn nháp 45.000đ"}),
    ev("order_draft", {"draft": draft}),
    ev("agent_state", {"state": "thinking"}),
    ev("agent_state", {"state": "composing"}),
    ev("text_delta", {"delta": t2_text}),
    ev("message_completed", {"text": t2_text, "sources": []}),
    ev("agent_state", {"state": "idle"}),
    ev("done", {"reason": "completed", "usage": usage(2310, 74, 2)}),
])
turn3 = "".join([
    ev("run_started", {"run_id": "c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7"}),
    ev("agent_state", {"state": "thinking"}),
    ev("tool_started", {"call_id": "call_3", "tool": "get_order_status", "label": "Kiểm tra đơn"}),
    ev("agent_state", {"state": "searching"}),
    ev("tool_finished", {"call_id": "call_3", "tool": "get_order_status", "ok": True, "summary": "Quán đã nhận đơn"}),
    ev("agent_state", {"state": "thinking"}),
    ev("agent_state", {"state": "composing"}),
    ev("text_delta", {"delta": t3_text}),
    ev("message_completed", {"text": t3_text, "sources": []}),
    ev("agent_state", {"state": "idle"}),
    ev("done", {"reason": "completed", "usage": usage(2405, 21, 2)}),
])
(out / "agent_stream.sse").write_text(
    ": Turn 1 — POST /api/agent/chat/stream {\"message\":\"Mình muốn uống gì đó ít ngọt, không quá 50k\"}\n" + turn1
    + ": Turn 2 — POST /api/agent/chat/stream {\"message\":\"Đặt cho mình 1 trà chanh gừng mật ong\"}\n" + turn2
    + ": (customer clicks 'Xác nhận đặt món' -> POST /api/orders/drafts/3c9e51a07d2b4f6e8a1c9d0b2e4f6a8c/confirm {\"expected_total_vnd\":45000} -> 201 order_from_draft.json; admin confirms)\n"
    + ": Turn 3 — POST /api/agent/chat/stream {\"message\":\"Đơn của mình sao rồi?\"}\n" + turn3,
    encoding="utf-8", newline="\n")
print(sorted(p.name for p in out.iterdir()))
