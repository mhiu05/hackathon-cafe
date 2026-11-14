import json

import pytest
from agents.testing import ScriptedModel, assistant_message, function_call
from starlette.requests import Request

from app.agent.factory import build_agent
from app.agent.stream import AgentDeps, run_chat_stream
from app.api.agent import ChatRequest, chat
from app.errors import ApiError
from app.knowledge.retrieval import KnowledgeIndex
from .helpers import collect

CONV = "e" * 32


async def test_old_response_cleanup_cannot_release_the_next_run(client, settings):
    request = Request({"type": "http", "app": client.app})
    client.app.state.agent = build_agent(settings, model=ScriptedModel([[assistant_message("Hello")]]))
    first = await chat(ChatRequest(message="hi"), request, CONV)
    await collect(first.body_iterator)
    second = await chat(ChatRequest(message="next"), request, CONV)
    try:
        # Starlette runs this after the previous stream finishes. A later request
        # may already own the conversation by then.
        await first.background()
        with pytest.raises(ApiError) as exc:
            await chat(ChatRequest(message="third"), request, CONV)
        assert (exc.value.status, exc.value.code) == (409, "RUN_IN_PROGRESS")
    finally:
        await second.body_iterator.aclose()
        await second.background()


async def test_never_started_response_releases_its_own_guard(client):
    response = await chat(ChatRequest(message="hi"), Request({"type": "http", "app": client.app}), CONV)
    await response.body_iterator.aclose()
    await response.background()
    assert client.app.state.conversation_guard.acquire(CONV)
    client.app.state.conversation_guard.release(CONV)


async def test_malformed_model_tool_args_are_logged_and_model_recovers(settings, conn):
    model = ScriptedModel([[function_call("search_menu", "{bad", call_id="bad-args")],
                           [assistant_message("Mình chưa đọc được yêu cầu, bạn hỏi lại nhé.")]])
    deps = AgentDeps(settings, build_agent(settings, model=model), KnowledgeIndex.load(conn), None)
    ev = await collect(run_chat_stream(deps, CONV, "matcha"))
    assert ev[-1][1]["reason"] == "completed"
    failed = next(data for name, data in ev if name == "tool_finished")
    assert failed["call_id"] == "bad-args" and failed["ok"] is False
    assert not [data for name, data in ev if name == "error"]
    row = conn.execute("SELECT ok,error_code,args_json FROM agent_tool_calls").fetchone()
    assert row["ok"] == 0 and row["error_code"] == "TOOL_FAILED"
    assert isinstance(json.loads(row["args_json"]), dict)
    model.assert_complete()
