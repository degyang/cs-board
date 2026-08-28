#!/usr/bin/env python3
"""Cross-platform launcher for the local whiteboard workshop."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATE_DIR = ROOT / ".webapp"
BACKEND_URL = "http://127.0.0.1:18765/api/health"
FRONTEND_URL = "http://127.0.0.1:13000"
PIPELINE_VERSION = "narrated_deck_v8_oil_visual"


def venv_python() -> Path:
    return ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def request(url: str) -> bytes | None:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError):
        return None


def backend_ready() -> bool:
    payload = request(BACKEND_URL)
    if not payload:
        return False
    try:
        return json.loads(payload).get("pipeline_version") == PIPELINE_VERSION
    except json.JSONDecodeError:
        return False


def frontend_ready() -> bool:
    return request(FRONTEND_URL) is not None


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def lan_address() -> str | None:
    # Does not send traffic; it asks the OS which local interface has a route.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            address = sock.getsockname()[0]
        return address if not address.startswith("127.") else None
    except OSError:
        return None


def launch(command: list[str], cwd: Path, output: Path, error: Path) -> None:
    options: dict[str, object] = {"cwd": cwd, "stdout": output.open("w", encoding="utf-8"), "stderr": error.open("w", encoding="utf-8")}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        options["start_new_session"] = True
    subprocess.Popen(command, **options)


def main() -> int:
    python = venv_python()
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not python.exists():
        print("Python virtual environment was not found. Run the installation command in README first.", file=sys.stderr)
        return 1
    if not npm:
        print("Node.js/npm was not found. Install Node.js 22.13 or newer first.", file=sys.stderr)
        return 1
    if not (ROOT / "web" / "node_modules").is_dir() or not (ROOT / "video_renderer" / "node_modules").is_dir():
        print("Frontend or renderer dependencies are missing. Run npm ci in both web and video_renderer.", file=sys.stderr)
        return 1

    STATE_DIR.mkdir(exist_ok=True)
    print("Starting the whiteboard video workshop...")
    print(f"Local URL: {FRONTEND_URL}")
    if address := lan_address():
        print(f"LAN URL: http://{address}:13000")

    if not backend_ready() and port_in_use(18765):
        print("Port 18765 is occupied by an unavailable or older backend. Stop that process, then run the launcher again.", file=sys.stderr)
        return 1
    if not backend_ready():
        launch([str(python), "-m", "uvicorn", "webapp.server:app", "--host", "127.0.0.1", "--port", "18765"], ROOT, STATE_DIR / "backend-output.log", STATE_DIR / "backend-error.log")
    else:
        print("Backend is already running.")
    if not frontend_ready() and port_in_use(13000):
        print("Port 13000 is occupied by an unavailable frontend. Stop that process, then run the launcher again.", file=sys.stderr)
        return 1
    if not frontend_ready():
        launch([npm, "run", "dev"], ROOT / "web", STATE_DIR / "frontend-output.log", STATE_DIR / "frontend-error.log")
    else:
        print("Frontend is already running.")

    for _ in range(90):
        if backend_ready() and frontend_ready():
            print("Ready. Opening the browser...")
            webbrowser.open(FRONTEND_URL)
            return 0
        time.sleep(1)
    print("Startup failed. See .webapp/backend-error.log and .webapp/frontend-error.log.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
