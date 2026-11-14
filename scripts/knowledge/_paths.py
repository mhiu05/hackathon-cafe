"""Shared paths/constants for the knowledge pipeline scripts (collect -> normalize -> ingest -> verify)."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_DIR = REPO_ROOT / "biblio_cafe_kb_bundle"          # user-provided originals: READ-ONLY
KNOWLEDGE_DIR = REPO_ROOT / "data" / "knowledge"
RAW_DIR = KNOWLEDGE_DIR / "raw"                           # gitignored (third-party content)
RAW_WEB_DIR = RAW_DIR / "web"
RAW_APIFY_DIR = RAW_DIR / "apify"
CURATED_DIR = KNOWLEDGE_DIR / "curated"                   # hand-curated claims/events with citations
NORMALIZED_DIR = KNOWLEDGE_DIR / "normalized"
EMBEDDINGS_DIR = KNOWLEDGE_DIR / "embeddings"             # content-hash keyed embedding cache (committed)
EVAL_DIR = KNOWLEDGE_DIR / "eval"
SOURCES_CONFIG = Path(__file__).resolve().parent / "sources.json"

BRANCH_ID = "biblio-79-nguy-nhu-kon-tum"
BRAND_ID = "biblio-brand"


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data, *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
