"""Start the local FastAPI + Next.js prototype; Ctrl-C stops both children."""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument(
    "--dev",
    action="store_true",
    help="Use the development frontend with polling watchers",
)
args = parser.parse_args()
node = shutil.which("node")
if not node:
    bundled = (
        Path.home()
        / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
    )
    if bundled.exists():
        node = str(bundled)
if not node:
    sys.exit("Node.js 20.9+ is required. Install Node, then rerun.")
if not (ROOT / "frontend/node_modules/next/dist/bin/next").exists():
    sys.exit(
        "Install frontend dependencies first: cd frontend && pnpm install --frozen-lockfile"
    )
if not args.dev and not (ROOT / "frontend/.next/BUILD_ID").exists():
    sys.exit("Build frontend first: cd frontend && pnpm build")
env = os.environ.copy()
env["WATCHPACK_POLLING"] = "true"
processes = []


def stop(*_):
    for p in processes:
        if p.poll() is None:
            p.terminate()
    for p in processes:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    sys.exit(0)


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)
try:
    processes.append(
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=ROOT,
            env=env,
        )
    )
    command = [
        node,
        str(ROOT / "frontend/node_modules/next/dist/bin/next"),
        "dev" if args.dev else "start",
        "--hostname",
        "127.0.0.1",
        "--port",
        "3000",
    ]
    if args.dev:
        command.append("--webpack")
    processes.append(subprocess.Popen(command, cwd=ROOT / "frontend", env=env))
    print(
        "VoiceBridge AI: http://localhost:3000 · API: http://localhost:8000/docs",
        flush=True,
    )
    while all(p.poll() is None for p in processes):
        time.sleep(0.5)
finally:
    stop()
