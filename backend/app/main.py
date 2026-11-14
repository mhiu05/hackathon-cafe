from __future__ import annotations

from contextlib import asynccontextmanager, closing

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import public, orders
from app.db.connection import connect
from app.db.migrate import apply_migrations
from app.errors import install_error_handlers
from app.knowledge.embeddings import VoyageEmbedder
from app.knowledge.retrieval import KnowledgeIndex
from app.settings import Settings, load_settings
from app.realtime.bus import EventBus


def create_app(settings: Settings | None = None) -> FastAPI:
    s = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = s
        app.state.bus = EventBus()
        with closing(connect(s.database_path)) as conn:
            apply_migrations(conn)
            app.state.index = KnowledgeIndex.load(conn)
        app.state.embedder = (VoyageEmbedder(s.voyage_api_key, s.voyage_embedding_model,
            s.voyage_embedding_dimension, timeout_s=5, max_retries=0) if s.voyage_api_key else None)
        yield

    app = FastAPI(lifespan=lifespan)
    install_error_handlers(app)
    app.add_middleware(CORSMiddleware, allow_origins=[s.frontend_origin], allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-Conversation-Id", "Idempotency-Key", "Authorization"],
        expose_headers=["Idempotent-Replay"])
    app.include_router(public.router)
    app.include_router(orders.router)
    return app


app = create_app()
