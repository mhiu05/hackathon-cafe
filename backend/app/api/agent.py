from __future__ import annotations

from typing import Annotated
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.stream import AgentDeps, run_chat_stream
from app.deps import require_conversation_id
from app.errors import ApiError
from app.realtime.sse import sse_response, with_heartbeat
from starlette.background import BackgroundTask

router = APIRouter(prefix="/api/agent")


class ConversationGuard:
    def __init__(self) -> None:
        self._active: set[str] = set()
        self._messages: dict[str, deque[float]] = defaultdict(deque)

    def acquire(self, conversation_id: str) -> bool:
        if conversation_id in self._active:
            return False
        self._active.add(conversation_id)
        return True

    def release(self, conversation_id: str) -> None:
        self._active.discard(conversation_id)

    def allow_message(self, conversation_id: str) -> bool:
        now = time.monotonic()
        entries = self._messages[conversation_id]
        while entries and entries[0] <= now - 60:
            entries.popleft()
        if len(entries) >= 20:
            return False
        entries.append(now)
        return True


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: Annotated[str, Field(min_length=1, max_length=1000)]

    @field_validator("message", mode="before")
    @classmethod
    def trim(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


@router.post("/chat/stream")
async def chat(body: ChatRequest, request: Request, conversation_id: str = Depends(require_conversation_id)) -> Response:
    state = request.app.state
    guard = state.conversation_guard
    if not guard.acquire(conversation_id):
        raise ApiError(409, "RUN_IN_PROGRESS", "Trợ lý đang xử lý tin nhắn trước, bạn đợi một chút nhé.")
    if not guard.allow_message(conversation_id):
        guard.release(conversation_id)
        raise ApiError(429, "RATE_LIMITED", "Bạn gửi quá nhiều tin nhắn, vui lòng đợi một phút.")
    deps = AgentDeps(state.settings, state.agent, state.index, state.embedder)

    async def guarded():
        stream = run_chat_stream(deps, conversation_id, body.message)
        try:
            async for chunk in stream:
                yield chunk
        finally:
            await stream.aclose()
            guard.release(conversation_id)

    response = sse_response(with_heartbeat(guarded()))
    response.background = BackgroundTask(guard.release, conversation_id)
    return response
