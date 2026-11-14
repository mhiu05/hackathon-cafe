from __future__ import annotations

import sqlite3
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.admin import auth
from app.catalog.repository import get_menu_item
from app.db.connection import transaction
from app.deps import get_db, require_admin
from app.errors import ApiError
from app.orders import service
from app.orders.state import allowed_next
from app.realtime.sse import format_sse, sse_response, with_heartbeat
from app.staff import service as staff
from app.timeutil import utc_now

OrderStatus = Literal["pending", "confirmed", "preparing", "ready", "completed", "rejected", "cancelled"]
Availability = Literal["available", "sold_out", "unknown"]
router = APIRouter(prefix="/api/admin")
protected = APIRouter(dependencies=[Depends(require_admin)])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pin: Annotated[str, Field(max_length=100)]


class UpdateStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to_status: OrderStatus
    expected_status: OrderStatus
    reason: Annotated[str | None, Field(max_length=200)] = None


class UpdateMenu(BaseModel):
    model_config = ConfigDict(extra="forbid")
    availability: Availability | None = None
    availability_note: Annotated[str | None, Field(max_length=200)] = None
    is_orderable: Annotated[bool | None, Field(strict=True)] = None


def admin_order(order: dict) -> dict:
    return {**order, "allowed_next": allowed_next(order["status"])}


@router.post("/login")
async def login(body: LoginRequest, request: Request, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return auth.login(conn, request.app.state.settings, body.pin,
        request.client.host if request.client else "unknown", request.app.state.login_limiter)


@protected.post("/logout", status_code=204)
def logout(token: str = Depends(require_admin), conn: sqlite3.Connection = Depends(get_db)) -> Response:
    auth.logout(conn, token)
    return Response(status_code=204)


@protected.get("/orders")
def orders(status: OrderStatus | None = None, limit: Annotated[int, Query(ge=1, le=200)] = 50,
           conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return {"orders": [admin_order(o) for o in service.list_orders(conn, status=status, limit=limit)], "counts": service.order_counts(conn)}


@protected.get("/orders/{order_id}")
def order(order_id: int, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return admin_order(service.get_order(conn, order_id=order_id))


@protected.patch("/orders/{order_id}/status")
async def update_status(order_id: int, body: UpdateStatus, request: Request, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    order = service.transition_status(conn, order_id=order_id, **body.model_dump())
    request.app.state.bus.publish("admin", "order_updated", {"order": order})
    request.app.state.bus.publish(f"order:{order_id}", "order_status", {"order": order})
    return admin_order(order)


@protected.patch("/menu/{item_id}")
def update_menu(item_id: str, body: UpdateMenu, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    fields = body.model_dump(exclude_unset=True)
    if any(fields.get(k, "missing") is None for k in ("availability", "is_orderable")):
        raise ApiError(422, "VALIDATION_ERROR", "Trạng thái món không được để trống.")
    with transaction(conn):
        get_menu_item(conn, item_id)
        for key, value in fields.items():
            # The field names come exclusively from UpdateMenu's fixed schema.
            conn.execute(f"UPDATE menu_items SET {key}=?,updated_at=? WHERE id=?", (value, utc_now(), item_id))
        return get_menu_item(conn, item_id)


class ResolveStaffRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["done"]


@protected.get("/staff-requests")
def staff_requests(status: Literal["open", "done"] | None = None, limit: Annotated[int, Query(ge=1, le=200)] = 50,
                   conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return {"requests": staff.list_requests(conn, status=status, limit=limit)}


@protected.patch("/staff-requests/{request_id}")
def resolve_staff_request(request_id: int, body: ResolveStaffRequest, request: Request,
                          conn: sqlite3.Connection = Depends(get_db)) -> dict:
    resolved = staff.resolve_request(conn, request_id)
    request.app.state.bus.publish("admin", "staff_request_updated", {"request": resolved})
    return resolved


@protected.get("/stream")
async def stream(request: Request) -> Response:
    async def events():
        async with request.app.state.bus.subscribe("admin") as subscription:
            async for name, data in subscription:
                yield format_sse(name, data)
    return sse_response(with_heartbeat(events()))


@protected.get("/insights")
def insights(conn: sqlite3.Connection = Depends(get_db)) -> dict:
    counts = service.order_counts(conn)
    revenue = conn.execute("SELECT COALESCE(SUM(total_vnd),0) FROM orders WHERE status='completed'").fetchone()[0]
    top = [dict(r) for r in conn.execute("SELECT oi.item_id,m.name,SUM(oi.quantity) AS quantity FROM order_items oi "
        "JOIN menu_items m ON m.id=oi.item_id GROUP BY oi.item_id,m.name ORDER BY quantity DESC,oi.item_id LIMIT 5")]
    runs = conn.execute("SELECT COUNT(*) AS runs,COALESCE(SUM(input_tokens),0) AS input_tokens,COALESCE(SUM(output_tokens),0) AS output_tokens FROM agent_runs").fetchone()
    tools = {r["tool"]: r["n"] for r in conn.execute("SELECT tool,COUNT(*) AS n FROM agent_tool_calls GROUP BY tool")}
    errors = conn.execute("SELECT COUNT(*) FROM agent_tool_calls WHERE ok=0").fetchone()[0]
    return {"orders_by_status": counts, "orders_total": sum(counts.values()), "revenue_completed_vnd": revenue,
        "top_items": top, "agent": {**dict(runs), "tool_calls": tools, "tool_errors": errors}}


router.include_router(protected)
