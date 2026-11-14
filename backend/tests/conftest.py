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
