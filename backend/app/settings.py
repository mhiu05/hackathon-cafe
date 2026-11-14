"""Runtime settings loaded from the repository-root `.env` plus process environment.

Process environment wins over `.env`. Secrets are never logged; use `Settings.redacted()` for display.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = ""
    voyage_api_key: str = ""
    apify_api_token: str = ""
    openai_model: str = "gpt-6-luna"
    voyage_embedding_model: str = "voyage-4-lite"
    voyage_embedding_dimension: int = 512
    database_path: Path = REPO_ROOT / "data" / "cafe.db"
    enable_apify_live_search: bool = False
    enable_agent_tracing: bool = True
    admin_pin: str = ""
    agent_sessions_db_path: Path = REPO_ROOT / "data" / "agent_sessions.db"
    frontend_origin: str = "http://localhost:5173"

    def redacted(self) -> dict[str, object]:
        secret = {"openai_api_key", "voyage_api_key", "apify_api_token", "admin_pin"}
        return {
            f.name: ("<set>" if getattr(self, f.name) else "<missing>") if f.name in secret else getattr(self, f.name)
            for f in fields(self)
        }


def load_settings(env_file: Path | None = None) -> Settings:
    """Merge `.env` (default: repo root) with os.environ and return typed settings."""
    merged = _read_dotenv(env_file or REPO_ROOT / ".env")
    merged.update({k: v for k, v in os.environ.items() if k.isupper()})

    def _path(key: str, default: str) -> Path:
        p = Path(merged.get(key, default))
        return p if p.is_absolute() else (REPO_ROOT / p).resolve()

    return Settings(
        openai_api_key=merged.get("OPENAI_API_KEY", ""),
        voyage_api_key=merged.get("VOYAGE_API_KEY", ""),
        apify_api_token=merged.get("APIFY_API_TOKEN", ""),
        openai_model=merged.get("OPENAI_MODEL", "gpt-6-luna"),
        voyage_embedding_model=merged.get("VOYAGE_EMBEDDING_MODEL", "voyage-4-lite"),
        voyage_embedding_dimension=int(merged.get("VOYAGE_EMBEDDING_DIMENSION", "512")),
        database_path=_path("DATABASE_PATH", "./data/cafe.db"),
        enable_apify_live_search=_as_bool(merged.get("ENABLE_APIFY_LIVE_SEARCH", "false")),
        enable_agent_tracing=_as_bool(merged.get("ENABLE_AGENT_TRACING", "true")),
        admin_pin=merged.get("ADMIN_PIN", ""),
        agent_sessions_db_path=_path("AGENT_SESSIONS_DB_PATH", "./data/agent_sessions.db"),
        frontend_origin=merged.get("FRONTEND_ORIGIN", "http://localhost:5173"),
    )
