"""Real-process tests for the fail-closed media preflight command."""

from __future__ import annotations

import contextlib
import http.server
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_media_preflight.py"
SPEC = importlib.util.spec_from_file_location("media_preflight", SCRIPT)
assert SPEC and SPEC.loader
preflight = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = preflight
SPEC.loader.exec_module(preflight)


class _Handler(http.server.BaseHTTPRequestHandler):
    status = 200
    body = b"{}"
    delay = 0.0

    def do_GET(self) -> None:  # noqa: N802
        if self.delay:
            time.sleep(self.delay)
        self.send_response(self.status)
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_: object) -> None:
        pass


@contextlib.contextmanager
def _server(status: int = 200, body: bytes = b"{}", delay: float = 0.0):
    handler = type("ControlledHandler", (_Handler,), {"status": status, "body": body, "delay": delay})
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=False)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        assert not thread.is_alive()


class MediaPreflightTest(unittest.TestCase):
    def _layout(self, directory: Path, endpoint: str) -> tuple[Path, Path]:
        root = directory / "repo"
        renderer = root / "video_renderer"
        renderer.mkdir(parents=True)
        for name in ("render.mjs", "align.mjs"):
            (renderer / name).write_text("// entry\n", encoding="utf-8")
        model = renderer / ".cache" / "models" / "ggml-medium.bin"
        model.parent.mkdir(parents=True)
        model.write_bytes(b"model")
        data = directory / "runtime"
        (data / "temp").mkdir(parents=True)
        services = data / "settings" / "services"
        services.mkdir(parents=True)
        (services / "tts.json").write_text(json.dumps({"enabled": True, "adapter_type": "indextts", "config": {"url": endpoint, "mode": "gradio"}}), encoding="utf-8")
        (services / "whisper.json").write_text(json.dumps({"enabled": True, "adapter_type": "whisper", "config": {"mode": "node", "model": "medium"}}), encoding="utf-8")
        return root, data

    def _bins(self, directory: Path) -> Path:
        bins = directory / "bin"
        bins.mkdir()
        for name in ("ffmpeg", "ffprobe", "node"):
            path = bins / name
            path.write_text("#!/bin/sh\necho '" + name + " test-version'\n", encoding="utf-8")
            path.chmod(0o755)
        return bins

    def _command(self, root: Path, data: Path, bins: Path) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "PATH": f"{bins}{os.pathsep}{os.environ.get('PATH', '')}"}
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), "--data-dir", str(data), "--json"], text=True, capture_output=True, env=env, timeout=8, check=False)

    def test_ready_exit_zero_uses_real_version_children_and_cleans_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw, _server(body=b"ok") as endpoint:
            directory = Path(raw)
            root, data = self._layout(directory, endpoint)
            completed = self._command(root, data, self._bins(directory))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertTrue(report["ready"])
            self.assertTrue(all(item["state"] == "ready" for item in report["items"]))
            versions = [item for item in report["items"] if item["name"] in {"ffmpeg", "ffprobe", "node"}]
            self.assertTrue(all(item["exit_code"] == 0 and item["signal"] is None for item in versions))
            self.assertEqual(list((data / "temp").iterdir()), [])

    def test_http_failure_and_missing_model_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw, _server(status=503) as endpoint:
            directory = Path(raw)
            root, data = self._layout(directory, endpoint)
            (root / "video_renderer" / ".cache" / "models" / "ggml-medium.bin").unlink()
            completed = self._command(root, data, self._bins(directory))
            self.assertNotEqual(completed.returncode, 0)
            reasons = {item["reason_code"] for item in json.loads(completed.stdout)["items"]}
            self.assertIn("HTTP_503", reasons)
            self.assertIn("MODEL_PATH_NOT_FOUND", reasons)

    def test_controlled_http_4xx_fails_closed_with_distinct_reason(self) -> None:
        with tempfile.TemporaryDirectory() as raw, _server(status=404) as endpoint:
            directory = Path(raw)
            root, data = self._layout(directory, endpoint)
            completed = self._command(root, data, self._bins(directory))
            self.assertNotEqual(completed.returncode, 0)
            reasons = {item["reason_code"] for item in json.loads(completed.stdout)["items"]}
            self.assertIn("HTTP_404", reasons)

    def test_silent_http_and_injected_artifact_failure_leave_no_residue(self) -> None:
        with tempfile.TemporaryDirectory() as raw, _server(delay=0.3) as endpoint:
            directory = Path(raw)
            root, data = self._layout(directory, endpoint)
            report = preflight.check(root, data, 0.05, inject_artifact_failure=True)
            reasons = {item["reason_code"] for item in report["items"]}
            self.assertIn("HTTP_TIMEOUT", reasons)
            self.assertIn("TEMP_ATOMIC_WRITE_FAILED", reasons)
            self.assertEqual(list((data / "temp").iterdir()), [])

    def test_invalid_endpoint_is_sanitized_and_optional_service_does_not_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            root, data = self._layout(directory, "http://user:secret@127.0.0.1:bad")
            service = data / "settings" / "services" / "tts.json"
            service.write_text(json.dumps({"enabled": True, "adapter_type": "indextts", "config": {"url": "http://user:secret@127.0.0.1:bad", "required": False}}), encoding="utf-8")
            report = preflight.check(root, data, 0.1)
            tts = next(item for item in report["items"] if item["name"] == "indextts")
            self.assertEqual(tts["reason_code"], "ENDPOINT_INVALID")
            self.assertNotIn("secret", json.dumps(report))

    def test_fastapi_malformed_health_response_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw, _server(body=b"not-json") as endpoint:
            directory = Path(raw)
            root, data = self._layout(directory, endpoint)
            service = data / "settings" / "services" / "tts.json"
            service.write_text(json.dumps({"enabled": True, "adapter_type": "indextts", "config": {"url": endpoint, "mode": "fastapi"}}), encoding="utf-8")
            report = preflight.check(root, data, 0.2)
            tts = next(item for item in report["items"] if item["name"] == "indextts")
            self.assertEqual(tts["reason_code"], "HTTP_MALFORMED_RESPONSE")
