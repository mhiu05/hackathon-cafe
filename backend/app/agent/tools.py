from __future__ import annotations

import json
from contextlib import closing
from datetime import datetime, timezone
from typing import Annotated, Literal

from agents import RunContextWrapper, function_tool
from pydantic import BaseModel, ConfigDict, Field

from app.agent.context import AgentContext
from app.catalog.dto import cafe_profile_dto, menu_response_dto, source_refs
from app.catalog.repository import coworking_info, recommend_items, search_menu_items
from app.db.connection import connect
from app.errors import ApiError
from app.knowledge.retrieval import asearch_knowledge
from app.orders.service import LineInput, create_draft, get_order, list_orders

Category = Literal["ca-phe", "sua-chua-cacao", "tra-lanh", "nuoc-ep", "matcha", "sinh-to", "mi-tom", "banh-bao", "an-vat"]
KBCategory = Literal["branches", "coworking", "customer_insights", "events", "facilities", "faq", "food_beverage", "location", "opening_hours", "overview", "room_rental"]
Tag = Literal["an-no", "an-vat", "beo-ngay", "ca-cao", "ca-phe", "co-caffeine", "co-topping", "hoa-thao-moc", "lanh", "matcha", "nuoc-ep", "sinh-to", "sua-chua", "tra", "trai-cay", "vi-chua"]
Budget = Annotated[int | None, Field(ge=10000, le=500000)]


def as_tool_json(payload: dict) -> str:
    return json.dumps({"ok": True, **payload}, ensure_ascii=False, separators=(",", ":"))


def tool_failure(ctx: RunContextWrapper[AgentContext], error: Exception) -> str:
    if isinstance(error, ApiError):
        return as_tool_json({"ok": False, "error": {"code": error.code, "message": error.message}})
    return as_tool_json({"ok": False, "error": {"code": "TOOL_FAILED", "message": "Công cụ tạm lỗi; xin lỗi khách và gợi ý xem Menu hoặc hỏi nhân viên."}})


@function_tool(timeout=5, failure_error_function=tool_failure, timeout_error_function=tool_failure)
async def get_cafe_info(ctx: RunContextWrapper[AgentContext], topic: Literal["all", "hours", "contact", "location", "wifi", "channels", "rating", "highlights"] = "all") -> str:
    """Read verified branch information; never return a Wi-Fi password."""
    with closing(connect(ctx.context.db_path)) as conn:
        profile = cafe_profile_dto(conn, datetime.now(timezone.utc))
    fields = {"hours": ["opening_hours", "is_open_now"], "contact": ["phone"], "location": ["address", "latitude", "longitude", "plus_code"],
        "wifi": ["wifi"], "channels": ["channels"], "rating": ["rating_snapshot"], "highlights": ["highlights"]}
    for source in profile["sources"]:
        ctx.context.sources[source["source_id"]] = source
    data = profile if topic == "all" else {k: profile[k] for k in fields[topic]}
    return as_tool_json({"data": data, "sources": profile["sources"], "data_notice": profile["data_notice"]})


@function_tool(timeout=8, failure_error_function=tool_failure, timeout_error_function=tool_failure)
async def search_cafe_knowledge(ctx: RunContextWrapper[AgentContext], query: Annotated[str, Field(min_length=2, max_length=300)],
                                category: KBCategory | None = None, top_k: Annotated[int, Field(ge=1, le=8)] = 5) -> str:
    """Retrieve actual café documents, attribution and evidence; no menu price or order status guessing."""
    with closing(connect(ctx.context.db_path)) as conn:
        result = await asearch_knowledge(conn, ctx.context.index, ctx.context.embedder, query, top_k=top_k,
            categories={category} if category else None)
        ids = list(dict.fromkeys(s for h in result.hits for s in (h.source_id, *h.citations)))
        for source in source_refs(conn, ids):
            ctx.context.sources[source["source_id"]] = source
    hits = []
    for hit in result.hits:
        data = hit.to_dict()
        hits.append({k: data[k] for k in ("title", "category", "content_kind", "verification_status", "source_title", "source_url", "retrieved_at", "score", "citations")} | {"content": hit.content[:700]})
    return as_tool_json({"mode": result.mode, "hits": hits, **({"note": "no_evidence"} if not hits else {})})


@function_tool(timeout=5, failure_error_function=tool_failure, timeout_error_function=tool_failure)
async def search_menu(ctx: RunContextWrapper[AgentContext], query: Annotated[str | None, Field(max_length=100)] = None,
                      category_id: Category | None = None, max_price_vnd: Budget = None,
                      kind: Literal["drink", "food", "any"] = "any", limit: Annotated[int, Field(ge=1, le=20)] = 10) -> str:
    """Search actual SQL menu items, variants and prices; all tokens in query must match the name."""
    with closing(connect(ctx.context.db_path)) as conn:
        data = search_menu_items(conn, query=query, category_id=category_id, max_price_vnd=max_price_vnd, kind=kind, limit=limit)
        data["price_basis"] = menu_response_dto(conn)["price_basis"]
    return as_tool_json(data)


@function_tool(timeout=5, failure_error_function=tool_failure, timeout_error_function=tool_failure)
async def recommend_drinks(ctx: RunContextWrapper[AgentContext], preferences: Annotated[list[Tag], Field(max_length=5)] = [],
                           max_price_vnd: Budget = None, include_food: bool = False,
                           exclude_item_ids: Annotated[list[str], Field(max_length=20)] = [], limit: Annotated[int, Field(ge=1, le=5)] = 3) -> str:
    """Recommend SQL menu items by inferred name tags and budget; tags do not establish sweetness or ingredients."""
    with closing(connect(ctx.context.db_path)) as conn:
        items = recommend_items(conn, preferences=preferences, max_price_vnd=max_price_vnd, include_food=include_food, exclude_item_ids=exclude_item_ids, limit=limit)
    return as_tool_json({"items": items, "basis": "Tags suy luận từ tên món, không phải thông tin thành phần/độ ngọt đã xác minh."})


@function_tool(timeout=5, failure_error_function=tool_failure, timeout_error_function=tool_failure)
async def get_coworking_info(ctx: RunContextWrapper[AgentContext], topic: Literal["all", "coworking", "rooms"] = "all",
                            min_capacity: Annotated[int | None, Field(ge=1, le=300)] = None, need_tables: bool = False) -> str:
    """Read service prices and room capacities; this cannot check availability or make bookings."""
    with closing(connect(ctx.context.db_path)) as conn:
        return as_tool_json(coworking_info(conn, topic=topic, min_capacity=min_capacity, need_tables=need_tables))


class OrderLineArg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: Annotated[str, Field(pattern=r"^menu_\d{3}$")]
    variant_id: Annotated[str | None, Field(pattern=r"^menu_\d{3}:[a-z0-9-]+$")] = None
    quantity: Annotated[int, Field(strict=True, ge=1, le=10)]
    note: Annotated[str | None, Field(max_length=120)] = None


@function_tool(timeout=8, failure_error_function=tool_failure, timeout_error_function=tool_failure)
async def prepare_order(ctx: RunContextWrapper[AgentContext], lines: Annotated[list[OrderLineArg], Field(min_length=1, max_length=10)],
                        customer_name: Annotated[str | None, Field(max_length=40)] = None,
                        table_label: Annotated[str | None, Field(max_length=20)] = None,
                        note: Annotated[str | None, Field(max_length=200)] = None) -> str:
    """Prepare a draft only. Customer MUST click Xác nhận đặt món to create an actual order."""
    with closing(connect(ctx.context.db_path)) as conn:
        draft = create_draft(conn, conversation_id=ctx.context.conversation_id,
            lines=[LineInput(**l.model_dump()) for l in lines], customer_name=customer_name, table_label=table_label, note=note)
    return as_tool_json({"draft": draft, "instruction": "Khách cần bấm 'Xác nhận đặt món' trên thẻ để gửi đơn."})


@function_tool(timeout=5, failure_error_function=tool_failure, timeout_error_function=tool_failure)
async def get_order_status(ctx: RunContextWrapper[AgentContext], order_code: Annotated[str | None, Field(pattern=r"^BB-\d{4,}$")] = None) -> str:
    """Read true status; without a code return only the latest three orders of this conversation."""
    with closing(connect(ctx.context.db_path)) as conn:
        orders = [get_order(conn, code=order_code)] if order_code else list_orders(conn, conversation_id=ctx.context.conversation_id, limit=3)
    return as_tool_json({"orders": [{k: o[k] for k in ("code", "status", "status_label", "total_vnd", "updated_at", "lines")} for o in orders]})


ALL_TOOLS = [get_cafe_info, search_cafe_knowledge, search_menu, recommend_drinks, get_coworking_info, prepare_order, get_order_status]
