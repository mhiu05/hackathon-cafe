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
print('Live smoke: running explicit backend checks; credentials stay in memory.', flush=True)
result = subprocess.run(['pnpm.cmd', 'exec', 'playwright', 'test', *specs, '--workers=1', *args], cwd=repo / 'frontend', env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
output = result.stdout
for secret in (settings.admin_pin, settings.openai_api_key, settings.voyage_api_key, settings.apify_api_token):
    if secret:
        output = output.replace(secret, '[REDACTED]')
sys.stdout.write(output)
raise SystemExit(result.returncode)
