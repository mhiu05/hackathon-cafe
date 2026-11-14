"""Two offline backend rehearsals using real SQL/KB/tools and REST confirmation."""
import importlib.util
from pathlib import Path

from agents.testing import ScriptedModel, assistant_message, function_call
from fastapi.testclient import TestClient

from app.agent.factory import build_agent
from app.main import create_app
from agent.helpers import parse_sse

_spec = importlib.util.spec_from_file_location("reset_rehearsal", Path(__file__).resolve().parents[3] / "scripts/demo/reset_demo.py")
_reset = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_reset)


def test_backend_demo_rehearsal_twice(settings, conn, tmp_path):
    headers = {"X-Conversation-Id": "d" * 32}
    for rehearsal in range(2):
        counts = _reset.reset_demo(settings.database_path, settings.agent_sessions_db_path, tmp_path / "backups")
        assert counts["orders"] == 0 and counts["kb_chunks"] == 56
        with TestClient(create_app(settings)) as client:
            assert client.get("/api/cafe").json()["phone"] == "0976 214 224"
            assert len(client.get("/api/menu").json()["items"]) == 51
            auth = {"Authorization": "Bearer " + client.post("/api/admin/login", json={"pin": "246810"}).json()["token"]}

            def chat(steps, message):
                model = ScriptedModel(steps)
                client.app.state.agent = build_agent(settings, model=model)
                r = client.post("/api/agent/chat/stream", headers=headers, json={"message": message})
                events = parse_sse([r.text])
                assert r.status_code == 200 and events[-1][1]["reason"] == "completed"
                model.assert_complete()
                return events

            events = chat([[function_call("get_cafe_info", {"topic": "wifi"}, call_id="wifi"),
                            function_call("search_cafe_knowledge", {"query": "yên tĩnh học tập"}, call_id="knowledge")],
                           [assistant_message("Bạn hỏi nhân viên mật khẩu Wi-Fi nhé.")]], "Quán có chỗ yên tĩnh ngồi học không? Wi-Fi thế nào?")
            assert next(data["sources"] for name, data in events if name == "message_completed")
            chat([[function_call("recommend_drinks", {"preferences": ["vi-chua", "tra"], "max_price_vnd": 50000}, call_id="recommend")],
                  [assistant_message("Mình chưa có thông tin độ ngọt đã xác minh.")]], "Gợi ý một món dưới 50k")
            events = chat([[function_call("search_menu", {"query": "trà chanh gừng mật ong"}, call_id="search")],
                           [function_call("prepare_order", {"lines": [{"item_id": "menu_024", "quantity": 1}]}, call_id="draft")],
                           [assistant_message("Bạn kiểm tra rồi bấm Xác nhận đặt món nhé.")]], "Lấy Trà chanh gừng mật ong nhé")
            draft = next(data["draft"] for name, data in events if name == "order_draft")
            assert draft["quote"]["total_vnd"] == 45000
            assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
            url = "/api/orders/drafts/" + draft["draft_id"] + "/confirm"
            created = client.post(url, json={"expected_total_vnd": 45000})
            replay = client.post(url, json={"expected_total_vnd": 45000})
            assert created.status_code == 201 and replay.status_code == 200
            assert created.json()["code"] == replay.json()["code"] == "BB-0001"
            assert client.get("/api/admin/orders", headers=auth).json()["counts"]["pending"] == 1
            for old, new in [("pending", "confirmed"), ("confirmed", "preparing"), ("preparing", "ready")]:
                assert client.patch("/api/admin/orders/1/status", headers=auth, json={"to_status": new, "expected_status": old}).status_code == 200
            assert client.get("/api/orders/BB-0001").json()["status"] == "ready"
            events = chat([[function_call("get_order_status", {}, call_id="status")],
                           [assistant_message("Sẵn sàng — mời bạn nhận tại quầy.")]], "Đơn của mình xong chưa?")
            assert next(data["summary"] for name, data in events if name == "tool_finished") == "Sẵn sàng — mời bạn nhận tại quầy"
            chat([[function_call("get_coworking_info", {"topic": "rooms", "min_capacity": 20}, call_id="room")],
                  [assistant_message("Mình chưa có dữ liệu phòng trống, bạn gọi quán nhé.")]], "Phòng nào cho 20 người?")
            assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert len(list((tmp_path / "backups").glob("cafe-*.db"))) == 2
