from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.stream import AgentDeps, run_chat_stream
from app.deps import require_conversation_id
from app.realtime.sse import sse_response, with_heartbeat

router = APIRouter(prefix="/api/agent")


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
    deps = AgentDeps(state.settings, state.agent, state.index, state.embedder)
    return sse_response(with_heartbeat(run_chat_stream(deps, conversation_id, body.message)))
