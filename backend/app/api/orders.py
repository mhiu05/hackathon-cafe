from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.deps import get_db, optional_conversation_id
from app.errors import ApiError
from app.orders import service
from app.realtime.sse import format_sse, sse_response, with_heartbeat

router = APIRouter(prefix="/api/orders")


class CartLine(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: str
    variant_id: str | None = None
    quantity: Annotated[int, Field(strict=True, ge=1, le=10)]
    note: Annotated[str | None, Field(max_length=120)] = None


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lines: list[CartLine]

    def inputs(self) -> list[service.LineInput]:
        return [service.LineInput(**l.model_dump()) for l in self.lines]


class CreateOrderRequest(QuoteRequest):
    expected_total_vnd: Annotated[int, Field(strict=True, gt=0)]
    customer_name: Annotated[str | None, Field(max_length=40)] = None
    table_label: Annotated[str | None, Field(max_length=20)] = None
    note: Annotated[str | None, Field(max_length=200)] = None


class ConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_total_vnd: Annotated[int, Field(strict=True, gt=0)]


def publish_order(request: Request, order: dict, replayed: bool) -> None:
    if not replayed:
        request.app.state.bus.publish("admin", "order_created", {"order": order})
        request.app.state.bus.publish(f"order:{order['id']}", "order_status", {"order": order})


def order_response(response: Response, replayed: bool) -> None:
    response.status_code = 200 if replayed else 201
    if replayed:
        response.headers["Idempotent-Replay"] = "true"


@router.post("/quote")
def quote(body: QuoteRequest, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return service.quote_cart(conn, body.inputs())


@router.post("")
async def create(body: CreateOrderRequest, request: Request, response: Response,
                 idempotency_key: str | None = Header(None), conversation_id: str | None = Depends(optional_conversation_id),
                 conn: sqlite3.Connection = Depends(get_db)) -> dict:
    if idempotency_key is None or not 8 <= len(idempotency_key) <= 100:
        raise ApiError(400, "BAD_REQUEST", "Idempotency-Key cần từ 8 đến 100 ký tự.")
    order, replayed = service.create_order(conn, lines=body.inputs(), expected_total_vnd=body.expected_total_vnd,
        customer_name=body.customer_name, table_label=body.table_label, note=body.note, source="ui",
        idempotency_key=idempotency_key, conversation_id=conversation_id)
    publish_order(request, order, replayed)
    order_response(response, replayed)
    return order


@router.get("/drafts/{draft_id}")
def draft(draft_id: str, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return service.get_draft(conn, draft_id)


@router.post("/drafts/{draft_id}/confirm")
async def confirm(draft_id: str, body: ConfirmRequest, request: Request, response: Response,
                  conn: sqlite3.Connection = Depends(get_db)) -> dict:
    order, replayed = service.confirm_draft(conn, draft_id=draft_id, expected_total_vnd=body.expected_total_vnd)
    publish_order(request, order, replayed)
    order_response(response, replayed)
    return order


@router.post("/drafts/{draft_id}/discard")
def discard(draft_id: str, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return service.discard_draft(conn, draft_id=draft_id)


@router.get("")
def listing(conversation_id: Annotated[str | None, Query(pattern=r"^[0-9a-f]{32}$")] = None,
            conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return {"orders": service.list_orders(conn, conversation_id=conversation_id)}


@router.get("/{code}")
def get(code: str, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    return service.get_order(conn, code=code)


@router.get("/{code}/stream")
async def order_stream(code: str, request: Request, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    order = service.get_order(conn, code=code)

    async def events():
        async with request.app.state.bus.subscribe(f"order:{order['id']}") as subscription:
            yield format_sse("order_status", {"order": service.get_order(conn, code=code)})
            async for name, data in subscription:
                yield format_sse(name, data)

    return sse_response(with_heartbeat(events()))
