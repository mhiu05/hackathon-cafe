import asyncio
import json

import httpx
import openai
import pytest
from agents import SQLiteSession
from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call

from app.api.agent import ConversationGuard
from app.agent.factory import build_agent
from app.agent.stream import AgentDeps, run_chat_stream
from app.knowledge.retrieval import KnowledgeIndex
from .helpers import collect

CONV = "a" * 32


def test_run_in_progress_returns_409():
    guard = ConversationGuard()
    assert guard.acquire(CONV) is True
    assert guard.acquire(CONV) is False
    guard.release(CONV)
    assert guard.acquire(CONV) is True


def test_rate_limit_twenty_per_minute():
    guard = ConversationGuard()
    assert all(guard.allow_message(CONV) for _ in range(20))
    assert guard.allow_message(CONV) is False
    assert guard.allow_message("b" * 32) is True


def test_rate_window_expires(monkeypatch):
    import app.api.agent as module
    now = [100.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: now[0])
    guard = ConversationGuard()
    for _ in range(20):
        assert guard.allow_message(CONV)
    now[0] = 160.01
    assert guard.allow_message(CONV)


def test_chat_requires_conversation_header(client):
    r = client.post("/api/agent/chat/stream", json={"message": "hi"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "BAD_REQUEST"


def test_guard_and_rate_limit_are_pre_stream_json_errors(client):
    h = {"X-Conversation-Id": CONV}
    guard = client.app.state.conversation_guard
    guard.acquire(CONV)
    r = client.post("/api/agent/chat/stream", headers=h, json={"message": "hi"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "RUN_IN_PROGRESS"
    guard.release(CONV)
    for _ in range(20):
        guard.allow_message(CONV)
    r = client.post("/api/agent/chat/stream", headers=h, json={"message": "hi"})
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED"
    assert guard.acquire(CONV)


def test_guard_released_after_model_failure(client, settings):
    err = openai.APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
    client.app.state.agent = build_agent(settings, model=ScriptedModel([ModelStep.raise_error(err)]))
    r = client.post("/api/agent/chat/stream", headers={"X-Conversation-Id": CONV}, json={"message": "hi"})
    assert 'MODEL_UNAVAILABLE' in r.text
    assert client.app.state.conversation_guard.acquire(CONV)


async def test_corrupt_tool_session_is_cleared(settings, conn, tmp_path):
    session = SQLiteSession("corrupt", tmp_path / "corrupt.db")
    await session.add_items([{"role": "user", "content": "earlier"}])
    err = openai.BadRequestError("No tool output found for function call", response=httpx.Response(400, request=httpx.Request("POST", "https://api.openai.com/v1/responses")), body={})
    deps = AgentDeps(settings, build_agent(settings, model=ScriptedModel([ModelStep.raise_error(err)])), KnowledgeIndex.load(conn), None)
    ev = await collect(run_chat_stream(deps, CONV, "hi", session=session))
    assert next(d for n,d in ev if n == "error")["code"] == "SESSION_RESET"
    assert await session.get_items() == []
    session.close()


async def test_max_turns_has_friendly_output_and_error(settings, conn, tmp_path):
    model = ScriptedModel([[function_call("search_menu", {"query": "matcha"}, call_id="loop" + str(i))] for i in range(8)])
    deps = AgentDeps(settings, build_agent(settings, model=model), KnowledgeIndex.load(conn), None)
    ev = await collect(run_chat_stream(deps, CONV, "loop", session=SQLiteSession("max", tmp_path / "max.db")))
    assert next(d for n,d in ev if n == "error")["code"] == "MAX_TURNS"
    assert any("hỏi ngắn hơn" in d["text"] for n,d in ev if n == "message_completed")
    assert ev[-1][1]["reason"] == "error"


async def test_cancelling_consumer_cancels_run(settings, conn):
    deps = AgentDeps(settings, build_agent(settings, model=ScriptedModel([[assistant_message("hi")]])), KnowledgeIndex.load(conn), None)
    gen = run_chat_stream(deps, CONV, "hi")
    assert "run_started" in await anext(gen)
    await gen.aclose()
    assert conn.execute("SELECT status FROM agent_runs").fetchone()[0] == "cancelled"


def test_real_model_timeout_and_retry_settings(settings):
    agent = build_agent(settings)
    assert agent.model == "gpt-6-luna"
    assert agent.model_settings.timeout == 30
    assert agent.model_settings.retry.max_retries == 2


async def test_transient_model_error_retries_then_completes(settings, conn):
    from dataclasses import replace
    from agents import ModelSettings
    err = openai.APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
    model = ScriptedModel([ModelStep.raise_error(err), ModelStep.raise_error(err), [assistant_message("Recovered")]])
    retry = replace(build_agent(settings).model_settings.retry, backoff={"initial_delay": 0, "max_delay": 0})
    agent = build_agent(settings, model=model).clone(model_settings=ModelSettings(retry=retry, timeout=30))
    ev = await collect(run_chat_stream(AgentDeps(settings, agent, KnowledgeIndex.load(conn), None), CONV, "hi"))
    assert ev[-1][1]["reason"] == "completed"
    assert len(model.calls) == 3


async def test_tool_timeout_returns_json_error_without_stopping_run(settings, conn):
    from dataclasses import replace
    from app.agent.tools import search_cafe_knowledge
    class SlowEmbedder:
        async def aembed_query(self, query):
            await asyncio.sleep(10)
    model = ScriptedModel([[function_call("search_cafe_knowledge", {"query": "parking"}, call_id="slow")],
                           [assistant_message("Please ask staff.")]])
    tool = replace(search_cafe_knowledge, timeout_seconds=.01)
    agent = build_agent(settings, model=model).clone(tools=[tool])
    deps = AgentDeps(settings, agent, KnowledgeIndex.load(conn), SlowEmbedder())
    ev = await collect(run_chat_stream(deps, CONV, "parking"))
    assert next(d for n,d in ev if n == "tool_finished")["ok"] is False
    assert ev[-1][1]["reason"] == "completed"


async def test_cancellation_while_model_is_running_persists_cancelled(settings, conn):
    started = asyncio.Event()
    async def slow(call):
        started.set()
        await asyncio.sleep(60)
        return [assistant_message("late")]
    agent = build_agent(settings, model=ScriptedModel([ModelStep.respond(slow)]))
    gen = run_chat_stream(AgentDeps(settings, agent, KnowledgeIndex.load(conn), None), CONV, "hi")
    await anext(gen)  # run_started
    await anext(gen)  # thinking
    pending = asyncio.create_task(anext(gen))
    await asyncio.wait_for(started.wait(), timeout=2)
    pending.cancel()
    await asyncio.gather(pending, return_exceptions=True)
    await gen.aclose()
    assert conn.execute("SELECT status FROM agent_runs").fetchone()[0] == "cancelled"
