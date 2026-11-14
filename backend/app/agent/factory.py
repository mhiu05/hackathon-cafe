from __future__ import annotations

from agents import Agent, Model, ModelSettings, RunConfig, SessionSettings
from agents.models.openai_provider import OpenAIProvider
from openai.types.shared import Reasoning

from app.agent.context import AgentContext
from app.agent.instructions import INSTRUCTIONS
from app.agent.tools import ALL_TOOLS
from app.settings import Settings


def build_agent(settings: Settings, *, model: Model | str | None = None) -> Agent[AgentContext]:
    selected = model or settings.openai_model
    return Agent(name="Biblio Concierge", instructions=INSTRUCTIONS, model=selected, tools=ALL_TOOLS,
        model_settings=ModelSettings(reasoning=Reasoning(effort="low"), verbosity="low") if isinstance(selected, str) else ModelSettings())


def build_run_config(settings: Settings, conversation_id: str, run_id: str) -> RunConfig:
    return RunConfig(workflow_name="biblio-concierge", group_id=conversation_id, trace_metadata={"run_id": run_id},
        tracing_disabled=not settings.enable_agent_tracing, trace_include_sensitive_data=False,
        model_provider=OpenAIProvider(api_key=settings.openai_api_key or "not-configured"), session_settings=SessionSettings(limit=40))
