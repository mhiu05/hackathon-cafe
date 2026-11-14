from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import closing
from dataclasses import dataclass
from uuid import uuid4

import openai
from agents import Agent, ItemHelpers, Runner, Session, SQLiteSession

from app.agent.context import AgentContext
from app.agent.factory import build_run_config
from app.db.connection import connect
from app.knowledge.embeddings import VoyageEmbedder
from app.knowledge.retrieval import KnowledgeIndex
from app.realtime.sse import format_sse
from app.settings import Settings
from app.timeutil import utc_now

TOOL_LABELS = {"get_cafe_info": "Xem thông tin quán", "search_cafe_knowledge": "Tra cứu tri thức về quán", "search_menu": "Tra menu",
    "recommend_drinks": "Đang tìm món hợp ý bạn", "get_coworking_info": "Xem co-working & phòng", "prepare_order": "Chuẩn bị đơn nháp", "get_order_status": "Kiểm tra đơn"}
MODEL_UNAVAILABLE = "Trợ lý tạm thời không khả dụng — bạn vẫn có thể đặt món từ Menu."


@dataclass
class AgentDeps:
    settings: Settings
    agent: Agent
    index: KnowledgeIndex
    embedder: VoyageEmbedder | None


def summarize_tool_output(tool: str, data: dict) -> str:
    if data.get("ok") is False:
        return data.get("error", {}).get("message", "Công cụ tạm lỗi.")
    if tool == "search_menu":
        return f"{data['total']} món"
    if tool == "recommend_drinks":
        return f"{len(data['items'])} gợi ý"
    if tool == "search_cafe_knowledge":
        return f"{len(data['hits'])} nguồn" if data["hits"] else "Không có bằng chứng"
    if tool == "get_coworking_info":
        return f"{len(data['packages'])} gói, {len(data['rooms'])} phòng"
    if tool == "prepare_order":
        return "Đơn nháp " + f"{data['draft']['quote']['total_vnd']:,}đ".replace(",", ".")
    if tool == "get_order_status":
        return data["orders"][0]["status_label"] if data["orders"] else "Chưa có đơn hàng"
    return "Đã xem thông tin quán"


def _truncate(value: object) -> object:
    if isinstance(value, str):
        return value[:200]
    if isinstance(value, dict):
        return {k: _truncate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate(v) for v in value]
    return value


async def run_chat_stream(deps: AgentDeps, conversation_id: str, message: str, *, session: Session | None = None) -> AsyncIterator[str]:
    run_id = uuid4().hex
    context = AgentContext(conversation_id, run_id, deps.settings.database_path, deps.index, deps.embedder)
    own_session = session is None
    session = session or SQLiteSession("chat-" + conversation_id, deps.settings.agent_sessions_db_path)
    result = None
    status, error_code = "running", None
    usage = {"input_tokens": 0, "output_tokens": 0, "requests": 0}
    calls: dict[str, tuple[str, float, str]] = {}
    composing = False
    with closing(connect(deps.settings.database_path)) as conn:
        conn.execute("INSERT INTO agent_runs(id,conversation_id,status,model,user_message_chars,started_at) VALUES (?,?,'running',?,?,?)",
            (run_id, conversation_id, deps.settings.openai_model, len(message), utc_now()))
        try:
            yield format_sse("run_started", {"run_id": run_id})
            yield format_sse("agent_state", {"state": "thinking"})
            result = Runner.run_streamed(deps.agent, message, context=context, session=session,
                run_config=build_run_config(deps.settings, conversation_id, run_id), max_turns=8)
            async for ev in result.stream_events():
                if ev.type == "raw_response_event" and ev.data.type == "response.output_text.delta":
                    if not composing:
                        composing = True
                        yield format_sse("agent_state", {"state": "composing"})
                    yield format_sse("text_delta", {"delta": ev.data.delta})
                elif ev.type == "run_item_stream_event":
                    if ev.name == "tool_called":
                        raw = ev.item.raw_item
                        calls[raw.call_id] = (raw.name, time.monotonic(), raw.arguments)
                        yield format_sse("tool_started", {"call_id": raw.call_id, "tool": raw.name, "label": TOOL_LABELS[raw.name]})
                        yield format_sse("agent_state", {"state": "working" if raw.name == "prepare_order" else "searching"})
                    elif ev.name == "tool_output":
                        cid = ev.item.call_id
                        tool, started, args = calls[cid]
                        try:
                            data = json.loads(ev.item.output)
                        except (ValueError, TypeError):
                            data = {"ok": False, "error": {"code": "TOOL_FAILED", "message": "Công cụ tạm lỗi."}}
                        ok = data.get("ok") is not False
                        conn.execute("INSERT INTO agent_tool_calls(run_id,call_id,tool,ok,error_code,latency_ms,args_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
                            (run_id, cid, tool, int(ok), data.get("error", {}).get("code"), int((time.monotonic()-started)*1000), json.dumps(_truncate(json.loads(args)), ensure_ascii=False), utc_now()))
                        yield format_sse("tool_finished", {"call_id": cid, "tool": tool, "ok": ok, "summary": summarize_tool_output(tool, data)})
                        if ok and "draft" in data:
                            yield format_sse("order_draft", {"draft": data["draft"]})
                        composing = False
                        yield format_sse("agent_state", {"state": "thinking"})
                    elif ev.name == "message_output_created":
                        yield format_sse("message_completed", {"text": ItemHelpers.text_message_output(ev.item), "sources": list(context.sources.values())})
                        composing = False
            status = "completed"
        except (asyncio.CancelledError, GeneratorExit):
            status = "cancelled"
            if result:
                result.cancel()
            raise
        except Exception as exc:
            status = "error"
            unavailable = isinstance(exc, (openai.APIConnectionError, openai.AuthenticationError, openai.RateLimitError)) or (isinstance(exc, openai.APIStatusError) and exc.status_code >= 500)
            error_code = "MODEL_UNAVAILABLE" if unavailable else "INTERNAL"
            logging.getLogger(__name__).warning("Agent run failed: %s", type(exc).__name__)
            yield format_sse("agent_state", {"state": "error"})
            yield format_sse("error", {"code": error_code, "message": MODEL_UNAVAILABLE if unavailable else "Trợ lý gặp lỗi, vui lòng thử lại.", "retryable": True})
        finally:
            if status == "running":
                status = "cancelled"
            if result:
                u = result.context_wrapper.usage
                usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens, "requests": u.requests}
            conn.execute("UPDATE agent_runs SET status=?,error_code=?,input_tokens=?,output_tokens=?,requests=?,finished_at=? WHERE id=?",
                (status, error_code, usage["input_tokens"], usage["output_tokens"], usage["requests"], utc_now(), run_id))
            if own_session:
                session.close()
        yield format_sse("agent_state", {"state": "idle"})
        yield format_sse("done", {"reason": status, "usage": usage})
