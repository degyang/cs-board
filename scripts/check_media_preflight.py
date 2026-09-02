#!/usr/bin/env python3
"""Fail-closed, side-effect-free readiness check for local media dependencies.

The command never starts a service or invokes media generation.  It only runs
bounded version commands, makes no-payload HTTP GET probes, and proves that a
temporary artifact directory can atomically write and clean up a small file.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


TIMEOUT_SECONDS = 2.0


def _result(name: str, state: str, reason_code: str | None = None, **extra: Any) -> dict[str, Any]:
    value: dict[str, Any] = {"name": name, "state": state, "reason_code": reason_code}
    value.update(extra)
    return value


def _safe_endpoint(value: str) -> str:
    """Return only scheme/host/port; credentials and paths never enter output."""
    parsed = urllib.parse.urlsplit(value)
    try:
        port = parsed.port
    except ValueError:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    host = parsed.hostname
    if port is not None:
        host = f"{host}:{port}"
    return f"{parsed.scheme}://{host}"


def _run_version(name: str, executable: str, timeout: float) -> dict[str, Any]:
    resolved = shutil.which(executable)
    if not resolved:
        return _result(name, "unavailable", "EXECUTABLE_NOT_FOUND")
    path = Path(resolved)
    if not path.is_file() or not os.access(path, os.X_OK):
        return _result(name, "misconfigured", "EXECUTABLE_NOT_RUNNABLE")
    try:
        completed = subprocess.run(
            [str(path), "--version"], capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return _result(name, "unavailable", "VERSION_TIMEOUT")
    except OSError:
        return _result(name, "unavailable", "VERSION_EXEC_FAILED")
    if completed.returncode != 0:
        return _result(name, "unavailable", "VERSION_FAILED", exit_code=completed.returncode)
    summary = (completed.stdout or completed.stderr).splitlines()
    return _result(name, "ready", version=(summary[0][:160] if summary else "reported"), exit_code=0, signal=None)


def _entry(name: str, path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _result(name, "unavailable", "ENTRY_NOT_FOUND")
    if not os.access(path, os.R_OK):
        return _result(name, "misconfigured", "ENTRY_NOT_READABLE")
    return _result(name, "ready")


def _path_check(name: str, raw: str | None, *, writable: bool = False) -> dict[str, Any]:
    if not raw:
        return _result(name, "unavailable", "MODEL_PATH_NOT_CONFIGURED")
    path = Path(raw).expanduser()
    if not path.exists():
        return _result(name, "unavailable", "MODEL_PATH_NOT_FOUND")
    if not path.is_file() and not path.is_dir():
        return _result(name, "misconfigured", "MODEL_PATH_INVALID_TYPE")
    if not os.access(path, os.R_OK):
        return _result(name, "misconfigured", "MODEL_PATH_NOT_READABLE")
    if writable and not os.access(path, os.W_OK):
        return _result(name, "misconfigured", "MODEL_PATH_NOT_WRITABLE")
    return _result(name, "ready")


def _http_probe(name: str, endpoint: str, probe_path: str, timeout: float, required: bool) -> dict[str, Any]:
    safe = _safe_endpoint(endpoint)
    if not safe:
        return _result(name, "misconfigured", "ENDPOINT_INVALID", required=required)
    request = urllib.request.Request(f"{safe}{probe_path}", method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310: configured local service
            status = response.status
            body = response.read(4096)
    except urllib.error.HTTPError as exc:
        return _result(name, "unavailable", f"HTTP_{exc.code}", required=required, endpoint=safe)
    except urllib.error.URLError as exc:
        code = "HTTP_TIMEOUT" if "timed out" in str(exc.reason).lower() else "HTTP_UNREACHABLE"
        return _result(name, "unavailable", code, required=required, endpoint=safe)
    except TimeoutError:
        return _result(name, "unavailable", "HTTP_TIMEOUT", required=required, endpoint=safe)
    if status < 200 or status >= 300:
        return _result(name, "unavailable", f"HTTP_{status}", required=required, endpoint=safe)
    if probe_path == "/health":
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _result(name, "misconfigured", "HTTP_MALFORMED_RESPONSE", required=required, endpoint=safe)
        if not isinstance(payload, dict):
            return _result(name, "misconfigured", "HTTP_MALFORMED_RESPONSE", required=required, endpoint=safe)
    return _result(name, "ready", required=required, endpoint=safe)


def _artifact_check(temp_dir: Path, inject_failure: bool = False) -> dict[str, Any]:
    if not temp_dir.is_dir():
        return _result("temp_artifact", "unavailable", "TEMP_DIR_NOT_FOUND")
    if not os.access(temp_dir, os.W_OK | os.X_OK):
        return _result("temp_artifact", "misconfigured", "TEMP_DIR_NOT_WRITABLE")
    workspace: Path | None = None
    try:
        workspace = Path(tempfile.mkdtemp(prefix="media-preflight-", dir=temp_dir))
        staging = workspace / "probe.staging"
        final = workspace / "probe.json"
        staging.write_text('{"probe":"ok"}\n', encoding="utf-8")
        if inject_failure:
            raise OSError("injected artifact failure")
        staging.replace(final)
        if final.read_text(encoding="utf-8") != '{"probe":"ok"}\n':
            return _result("temp_artifact", "misconfigured", "TEMP_READBACK_FAILED")
        return _result("temp_artifact", "ready")
    except OSError:
        return _result("temp_artifact", "unavailable", "TEMP_ATOMIC_WRITE_FAILED")
    finally:
        if workspace is not None:
            shutil.rmtree(workspace, ignore_errors=True)


def _services(data_dir: Path) -> list[dict[str, Any]]:
    directory = data_dir / "settings" / "services"
    if not directory.is_dir():
        return []
    values: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("enabled", True):
            values.append(value)
    return values


def check(root: Path, data_dir: Path, timeout: float, inject_artifact_failure: bool = False) -> dict[str, Any]:
    items = [
        _run_version("ffmpeg", "ffmpeg", timeout),
        _run_version("ffprobe", "ffprobe", timeout),
        _run_version("node", "node", timeout),
        _entry("renderer_entry", root / "video_renderer" / "render.mjs"),
        _entry("whisper_alignment_entry", root / "video_renderer" / "align.mjs"),
        _artifact_check(data_dir / "temp", inject_artifact_failure),
    ]
    tts_found = whisper_found = False
    for service in _services(data_dir):
        config = service.get("config") if isinstance(service.get("config"), dict) else {}
        adapter = str(service.get("adapter_type", "")).lower()
        capability = str(service.get("capability", "")).lower()
        required = bool(config.get("required", True))
        if adapter == "indextts" or capability == "speech_synthesis":
            tts_found = True
            endpoint = str(config.get("url") or service.get("endpoint") or "")
            probe_path = "/health" if str(config.get("mode", "gradio")) == "fastapi" else "/"
            items.append(_http_probe("indextts", endpoint, probe_path, timeout, required))
            model_path = config.get("model_path") or config.get("model_dir")
            if model_path:
                items.append(_path_check("indextts_model", model_path))
        if adapter == "whisper" or capability == "speech_alignment":
            whisper_found = True
            mode = str(config.get("mode", "node"))
            if mode == "http":
                items.append(_http_probe("whisper", str(config.get("base_url") or service.get("endpoint") or ""), "/health", timeout, required))
            else:
                model = str(config.get("model") or service.get("model") or "medium")
                items.append(_path_check("whisper_model", str(root / "video_renderer" / ".cache" / "models" / f"ggml-{model}.bin")))
    if not tts_found:
        items.append(_result("indextts", "unavailable", "SERVICE_NOT_CONFIGURED", required=True))
    if not whisper_found:
        items.append(_result("whisper", "unavailable", "SERVICE_NOT_CONFIGURED", required=True))
    ready = all(item["state"] == "ready" or item.get("required") is False for item in items)
    return {"schema_version": 1, "ready": ready, "items": items}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("CSBOARD_DATA_DIR", Path.home() / ".csboard")))
    parser.add_argument("--timeout", type=float, default=TIMEOUT_SECONDS)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--inject-artifact-failure", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    report = check(args.root.resolve(), args.data_dir.expanduser(), args.timeout, args.inject_artifact_failure)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
