"""Shared pytest fixtures. Tests never call OpenAI/Voyage/Apify unless marked `live`."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.db.connection import connect  # noqa: E402
from app.db.migrate import apply_migrations  # noqa: E402


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "live: calls real external APIs (OpenAI/Voyage); run with -m live")


@pytest.fixture()
def db(tmp_path: Path):
    """Fresh migrated database in a temp dir."""
    conn = connect(tmp_path / "test.db")
    apply_migrations(conn)
    yield conn
    conn.close()

import shutil, sqlite3
from contextlib import closing
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.db.connection import connect
from app.db.migrate import apply_migrations
from app.main import create_app
from app.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
ADMIN_PIN = "246810"

@pytest.fixture(scope="session")
def pristine_db(tmp_path_factory) -> Path:
    src = REPO_ROOT / "data" / "cafe.db"
    if not src.exists():
        pytest.skip("run: uv run python scripts/knowledge/ingest.py --offline")
    dst = tmp_path_factory.mktemp("pristine") / "cafe.db"
    with closing(connect(src, read_only=True)) as s, closing(sqlite3.connect(dst)) as d:
        s.backup(d)
    return dst

@pytest.fixture()
def db_path(pristine_db, tmp_path) -> Path:
    dst = tmp_path / "cafe.db"
    shutil.copy(pristine_db, dst)
    return dst

@pytest.fixture()
def settings(db_path, tmp_path) -> Settings:
    return Settings(openai_api_key="test-key", voyage_api_key="", database_path=db_path,
                    agent_sessions_db_path=tmp_path / "sessions.db", admin_pin=ADMIN_PIN, enable_agent_tracing=False)

@pytest.fixture()
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c

@pytest.fixture()
def conn(db_path):
    c = connect(db_path); apply_migrations(c)
    yield c
    c.close()
