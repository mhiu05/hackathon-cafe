"""Reset and rehearse an isolated Dev A snapshot twice, with bounded opt-in agent calls."""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--snapshot', type=Path, required=True)
parser.add_argument('--runs', type=int, choices=[1, 2], default=2)
parser.add_argument('--agent', action='store_true', help='Up to three real agent turns per rehearsal; no automatic retries.')
args = parser.parse_args()
repo = Path(__file__).resolve().parents[2]
snapshot = args.snapshot.resolve()
cache = (repo / 'frontend/node_modules/.cache').resolve()
reset = snapshot / 'scripts/demo/reset_demo.py'
if not snapshot.is_relative_to(cache) or not reset.is_file():
    parser.error('Provide a snapshot under frontend/node_modules/.cache containing scripts/demo/reset_demo.py')
python = sys.executable
flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
server: subprocess.Popen | None = None
server_log = (snapshot / 'rehearsal-server.log').open('ab')

def stop() -> None:
    global server
    if server and server.poll() is None:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
    server = None

def start() -> None:
    global server
    try:
        probe = socket.create_connection(('127.0.0.1', 8000), timeout=.2)
    except OSError:
        pass
    else:
        probe.close()
        raise RuntimeError('Port 8000 is already owned by another backend; stop it before isolated rehearsals.')
    server = subprocess.Popen([python, str(repo / 'frontend/scripts/serve_backend_snapshot.py'), '--snapshot', str(snapshot)],
                              cwd=repo, stdout=server_log, stderr=server_log, creationflags=flags)
    for _ in range(120):
        if server.poll() is not None:
            raise RuntimeError('Snapshot backend exited; inspect the local rehearsal-server.log')
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=1) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(.25)
    raise RuntimeError('Snapshot backend did not become ready within 30 seconds')

def run(command: list[str]) -> None:
    subprocess.run(command, cwd=repo, check=True, creationflags=flags)

def keep_images(label: str) -> None:
    target = snapshot / 'rehearsals' / label
    target.mkdir(parents=True, exist_ok=True)
    for image in (repo / 'frontend/test-results').glob('*.png'):
        shutil.copy2(image, target / image.name)

try:
    # Initialize migrations once; reset only while this owned server is stopped.
    start()
    stop()
    for rehearsal in range(1, args.runs + 1):
        print(f'Rehearsal {rehearsal}/{args.runs}: backup + reset isolated commerce data', flush=True)
        run([python, str(reset), '--db', str(snapshot / 'live-cafe.db'), '--sessions-db', str(snapshot / 'live-sessions.db'), '--backups-dir', str(snapshot / 'backups')])
        start()
        run([python, str(repo / 'frontend/scripts/run_live_smoke.py')])
        keep_images(f'run-{rehearsal}-cart')
        if args.agent:
            run([python, str(repo / 'frontend/scripts/run_live_smoke.py'), '--agent'])
            keep_images(f'run-{rehearsal}-agent')
        stop()
        print(f'Rehearsal {rehearsal}/{args.runs}: passed', flush=True)
finally:
    stop()
    server_log.close()
