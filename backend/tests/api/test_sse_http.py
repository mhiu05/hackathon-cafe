"""Exercise SSE over real HTTP: ASGI TestClient buffers endless streams."""
import asyncio
import json
import socket
import threading

import httpx
import uvicorn

from app.main import create_app


async def next_event(lines):
    name = None
    async for line in lines:
        if line.startswith("event: "):
            name = line[7:]
        elif line.startswith("data: "):
            return name, json.loads(line[6:])
    raise AssertionError("stream ended without event")


async def test_admin_transition_reaches_customer_and_admin_over_http(settings):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(settings), log_level="critical", lifespan="on"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        for _ in range(150):
            if server.started:
                break
            await asyncio.sleep(.02)
        assert server.started
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=5, trust_env=False) as c:
            r = await c.post("/api/orders", headers={"Idempotency-Key": "sse-http-key"}, json={"lines": [{"item_id": "menu_030", "quantity": 1}], "expected_total_vnd": 45000})
            assert r.status_code == 201
            token = (await c.post("/api/admin/login", json={"pin": "246810"})).json()["token"]
            h = {"Authorization": "Bearer " + token}
            async with c.stream("GET", "/api/orders/BB-0001/stream") as customer:
                assert customer.headers["x-accel-buffering"] == "no"
                customer_lines = customer.aiter_lines()
                event, data = await next_event(customer_lines)
                assert event == "order_status" and data["order"]["status"] == "pending"
                async with c.stream("GET", "/api/admin/stream", headers=h) as admin:
                    await asyncio.sleep(.05)
                    changed = await c.patch("/api/admin/orders/1/status", headers=h, json={"to_status": "confirmed", "expected_status": "pending"})
                    assert changed.status_code == 200
                    event, data = await next_event(customer_lines)
                    assert event == "order_status" and data["order"]["status"] == "confirmed"
                    event, data = await next_event(admin.aiter_lines())
                    assert event == "order_updated" and data["order"]["code"] == "BB-0001"
    finally:
        server.should_exit = True
        await asyncio.to_thread(thread.join, 5)
        sock.close()
        assert not thread.is_alive()
