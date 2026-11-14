"""Run an immutable Dev A backend snapshot against a separate local test database.

Export backend/ with git archive into frontend/node_modules/.cache first.
Never logs credentials and never rewrites backend source, root .env or the source DB.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--snapshot', type=Path, required=True)
parser.add_argument('--port', type=int, default=8000)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[2]
snapshot = args.snapshot.resolve()
cache = (repo / 'frontend' / 'node_modules' / '.cache').resolve()
if not snapshot.is_relative_to(cache) or not (snapshot / 'backend' / 'app' / 'main.py').is_file():
    parser.error('Snapshot must contain backend/app/main.py under frontend/node_modules/.cache')
database = snapshot / 'live-cafe.db'
if not database.exists():
    with sqlite3.connect(repo / 'data' / 'cafe.db') as source, sqlite3.connect(database) as target:
        source.backup(target)
sys.path.insert(0, str(snapshot / 'backend'))

import uvicorn  # noqa: E402
from app.settings import load_settings  # noqa: E402
from app.main import create_app  # noqa: E402

settings = replace(load_settings(repo / '.env'), database_path=database,
                   agent_sessions_db_path=snapshot / 'live-sessions.db', enable_agent_tracing=False)
uvicorn.run(create_app(settings), host='127.0.0.1', port=args.port, workers=1, log_level='warning')
