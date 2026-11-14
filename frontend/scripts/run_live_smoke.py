"""Pass the configured PIN in memory to Playwright; never print it or modify .env."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo / 'backend'))
from app.settings import load_settings  # noqa: E402

settings = load_settings(repo / '.env')
if not settings.admin_pin:
    raise SystemExit('ADMIN_PIN is not configured; live smoke requires the backend configuration.')
args = sys.argv[1:]
agent = '--agent' in args
args = [arg for arg in args if arg != '--agent']
env = dict(os.environ, E2E_ADMIN_PIN=settings.admin_pin, E2E_AGENT_LIVE='1' if agent else '0')
specs = ['e2e/agent-live.spec.ts'] if agent else ['e2e/demo.spec.ts']
raise SystemExit(subprocess.call(['pnpm.cmd', 'exec', 'playwright', 'test', *specs, '--workers=1', *args], cwd=repo / 'frontend', env=env))
