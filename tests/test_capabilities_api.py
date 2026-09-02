"""Contract tests for the native dynamic Mountain capabilities endpoint."""

from __future__ import annotations

import json
import time
from pathlib import Path

from starlette.testclient import TestClient

from csboard.adapters.filesystem.service_registry import _probe_cache
from webapp.mountain_server import create_app


def _client(tmp_path: Path) -> TestClient:
    _probe_cache.clear()
    return TestClient(create_app(tmp_path))


def test_capabilities_has_stable_sanitized_shape_without_probe(tmp_path: Path):
    response = _client(tmp_path).get("/api/v1/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "providers"}
    assert {item["visual_source"] for item in body["items"]} == {"preset", "custom-reference"}
    assert body["providers"]["all_available"] is False
    assert body["providers"]["providers"]
    assert all(set(value) == {"available", "component", "error_code", "suggestion"}
               for value in body["providers"]["providers"].values())
    assert any(value["error_code"] == "NOT_PROBED"
               for value in body["providers"]["providers"].values())
    encoded = response.text.lower()
    assert "top-secret" not in encoded
    assert "http://" not in encoded
    assert "https://" not in encoded


def test_capabilities_uses_cached_probe_but_keeps_external_illustrations_unavailable(tmp_path: Path):
    client = _client(tmp_path)
    _probe_cache["whiteboard-renderer"] = ({
        "available": True,
        "error_code": None,
    }, time.monotonic())
    _probe_cache["openai-compatible-image"] = ({
        "available": True,
        "error_code": None,
    }, time.monotonic())
    _probe_cache["local-ffmpeg"] = ({
        "available": False,
        "error_code": "FFMPEG_NOT_FOUND",
    }, time.monotonic())

    body = client.get("/api/v1/capabilities").json()
    providers = body["providers"]["providers"]
    assert providers["whiteboard-renderer"]["available"] is True
    assert providers["local-ffmpeg"]["error_code"] == "FFMPEG_NOT_FOUND"
    assert providers["openai-compatible-image"] == {
        "available": False,
        "component": "openai-compatible-image",
        "error_code": "SECRET_NOT_CONFIGURED",
        "suggestion": None,
    }
    assert body["providers"]["all_available"] is False


def test_capabilities_reports_configured_image_as_external_gate(tmp_path: Path):
    client = _client(tmp_path)
    settings = tmp_path / "settings" / "services" / "openai-compatible-image.json"
    service = json.loads(settings.read_text(encoding="utf-8"))
    # The registry's encrypted store is intentionally not populated; replacing
    # its required credential declaration models a fully configured local test
    # service without placing any credential value in test data.
    service["required_secrets"] = []
    settings.write_text(json.dumps(service), encoding="utf-8")

    body = client.get("/api/v1/capabilities").json()
    assert body["providers"]["providers"]["openai-compatible-image"]["error_code"] == "EXTERNAL_STAGE_GATE_REQUIRED"
    assert body["providers"]["all_available"] is False
