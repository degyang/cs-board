"""Contract tests for the native dynamic Mountain capabilities endpoint."""

from __future__ import annotations

import json
import time
from pathlib import Path

from starlette.testclient import TestClient

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry, _probe_cache
from csboard.adapters.secrets.secret_store import PlaintextSecretStore
from csboard.application.capabilities import CapabilityService
from csboard.domain.service_definition import ServiceDefinition
from webapp.mountain_server import create_app


def _client(tmp_path: Path) -> TestClient:
    _probe_cache.clear()
    return TestClient(create_app(tmp_path))


def _registry(tmp_path: Path) -> FilesystemServiceRegistry:
    _probe_cache.clear()
    return FilesystemServiceRegistry(tmp_path, PlaintextSecretStore(tmp_path / ".secrets"))


def _service(service_id: str, capability: str) -> ServiceDefinition:
    return ServiceDefinition(
        service_id=service_id,
        display_name=service_id,
        capability=capability,
        adapter_type="local_process",
        required_secrets=[],
    )


def _cache_available(service_id: str, available: bool = True) -> None:
    _probe_cache[service_id] = ({
        "available": available,
        "error_code": None if available else "PROBE_FAILED",
    }, time.monotonic())


def _ordinary_dynamic_services(registry: FilesystemServiceRegistry) -> None:
    for suffix, capability in (
        ("words", "text_generation"),
        ("voice", "speech_synthesis"),
        ("align", "speech_alignment"),
        ("draw", "rendering"),
        ("mux", "media"),
    ):
        service_id = f"custom-{suffix}"
        registry.create_service(_service(service_id, capability))
        _cache_available(service_id)


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


def test_api_uses_the_shared_capability_read_model(tmp_path: Path, monkeypatch):
    expected = {"items": [{"engine": "shared-read-model"}], "providers": {"all_available": False}}
    monkeypatch.setattr(CapabilityService, "snapshot", lambda _self: expected)

    response = _client(tmp_path).get("/api/v1/capabilities")

    assert response.status_code == 200
    assert response.json() == expected


def test_capability_service_handles_an_empty_dynamic_registry(tmp_path: Path):
    body = CapabilityService(_registry(tmp_path)).snapshot()

    assert body["providers"] == {"all_available": False, "providers": {}, "unavailable": []}
    assert body["items"][0]["supported"] is False
    assert body["items"][0]["reason_code"] == "CAPABILITY_NOT_AVAILABLE"


def test_dynamic_services_require_alignment_before_only_external_gate_remains(tmp_path: Path):
    registry = _registry(tmp_path)
    _ordinary_dynamic_services(registry)
    capabilities = CapabilityService(registry)

    all_ordinary_available = capabilities.snapshot()
    assert all_ordinary_available["providers"]["providers"]["custom-align"]["available"] is True
    assert all_ordinary_available["items"][0]["reason_code"] == "EXTERNAL_STAGE_GATE_REQUIRED"
    assert all_ordinary_available["providers"]["all_available"] is False

    _cache_available("custom-align", available=False)
    alignment_failed = capabilities.snapshot()
    assert alignment_failed["providers"]["providers"]["custom-align"]["error_code"] == "PROBE_FAILED"
    assert alignment_failed["items"][0]["reason_code"] == "CAPABILITY_NOT_AVAILABLE"


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
