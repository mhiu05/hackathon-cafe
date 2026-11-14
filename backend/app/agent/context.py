from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.knowledge.embeddings import VoyageEmbedder
from app.knowledge.retrieval import KnowledgeIndex
from app.realtime.bus import EventBus


@dataclass
class AgentContext:
    conversation_id: str
    run_id: str
    db_path: Path
    index: KnowledgeIndex
    embedder: VoyageEmbedder | None
    sources: dict[str, dict] = field(default_factory=dict)
    bus: EventBus | None = None  # admin topic for staff requests; None in unit tests without the app
