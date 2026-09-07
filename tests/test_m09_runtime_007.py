"""Offline regressions for bounded runtime readiness recovery."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend import mountain_server
from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.adapters.secrets.secret_store import PlaintextSecretStore
from csboard.application.capabilities import CapabilityService
from csboard.domain.service_definition import ServiceDefinition


def _registry(root: Path) -> FilesystemServiceRegistry:
    return FilesystemServiceRegistry(root, PlaintextSecretStore(root / ".secrets"))


def _service(service_id: str, capability: str, *, enabled: bool = True, config: dict | None = None) -> ServiceDefinition:
    return ServiceDefinition(
        service_id=service_id,
        display_name=service_id,
        capability=capability,
        adapter_type="local_process",
        required_secrets=[],
        enabled=enabled,
        config=config or {},
    )


def test_probe_cache_is_not_reused_by_a_different_data_root(tmp_path: Path):
    first = _registry(tmp_path / "first")
    first.create_service(_service("same-service", "media"))
    assert first.probe_service("same-service")["available"] is True

    second = _registry(tmp_path / "second")
    second.create_service(_service("same-service", "media"))
    assert second.get_cached_probe("same-service") is None
    assert first.get_cached_probe("same-service")["available"] is True


def test_readiness_probes_only_enabled_capability_prerequisites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    registry = _registry(tmp_path)
    registry.create_service(_service("text", "text_generation"))
    registry.create_service(_service("voice", "speech_synthesis"))
    registry.create_service(_service(
        "mimo", "audio_generation", config={"capabilities": ["speech_synthesis"]},
    ))
    registry.create_service(_service(
        "codeplan", "audio_generation", config={"capabilities": ["text_generation"]},
    ))
    registry.create_service(_service("disabled-media", "media", enabled=False))
    registry.create_service(_service("image", "image_generation"))
    called: list[str] = []

    def probe(service_id: str, *, force: bool = False) -> dict:
        called.append(service_id)
        assert force is True
        return {"available": True, "component": service_id}

    monkeypatch.setattr(registry, "probe_service", probe)
    results = registry.probe_enabled_readiness_services()

    assert set(called) == {"codeplan", "mimo"}
    by_component = {result["component"]: result for result in results}
    assert set(by_component) == {"codeplan", "mimo"}
    assert all(result["available"] for result in by_component.values())


def test_selected_readiness_probe_failure_is_recorded_without_startup_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    registry = _registry(tmp_path)
    registry.create_service(_service("voice", "speech_synthesis"))

    def probe(_service_id: str, *, force: bool = False) -> dict:
        assert force is True
        raise RuntimeError("offline")

    monkeypatch.setattr(registry, "probe_service", probe)
    result = registry.probe_enabled_readiness_services()

    assert result[0]["available"] is False
    assert result[0]["component"] == "voice"
    assert result[0]["error_code"] == "PROBE_ERROR"


def _ten_service_topology(registry: FilesystemServiceRegistry) -> None:
    for service in (
        _service("local-ffmpeg", "media"),
        _service("local-indextts", "speech_synthesis"),
        _service("local-whisper", "speech_alignment"),
        _service("mock-llm", "text_generation"),
        _service("codeplan", "audio_generation", config={"capabilities": ["audio_generation", "text_generation"]}),
        _service("mimo-chat", "text_generation", config={"capabilities": ["text_generation", "multimodal"]}),
        _service("mimo-tts", "audio_generation", config={"capabilities": ["audio_generation"]}),
        _service("openai-text", "text_generation"),
        _service("openai-image", "image_generation"),
        _service("whiteboard", "rendering"),
    ):
        registry.create_service(service)


def test_ten_service_startup_probes_match_accepted_four_service_cache_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    accepted = _registry(tmp_path / "accepted")
    restarted = _registry(tmp_path / "restarted")
    _ten_service_topology(accepted)
    _ten_service_topology(restarted)
    expected_ids = {"codeplan", "mimo-tts", "local-whisper", "local-ffmpeg"}

    def probe(service: ServiceDefinition):
        return (service.service_id in expected_ids, "UNREACHABLE", "unavailable")

    monkeypatch.setattr(accepted, "_do_probe", probe)
    monkeypatch.setattr(restarted, "_do_probe", probe)
    for service_id in expected_ids:
        assert accepted.probe_service(service_id, force=True)["available"] is True
    restarted.probe_enabled_readiness_services()

    all_ids = [service.service_id for service in accepted.list_services()]
    assert {service_id for service_id in all_ids if restarted.get_cached_probe(service_id)} == expected_ids
    accepted_capabilities = CapabilityService(accepted)
    restarted_capabilities = CapabilityService(restarted)
    accepted_services = accepted_capabilities._unique_services()
    restarted_services = restarted_capabilities._unique_services()
    accepted_bootstrap = accepted_capabilities._bootstrap_snapshot(accepted_services)
    restarted_bootstrap = restarted_capabilities._bootstrap_snapshot(restarted_services)
    assert accepted_capabilities._service_fingerprint(accepted_services, accepted_bootstrap["bootstrap_diagnostics"]) == (
        restarted_capabilities._service_fingerprint(restarted_services, restarted_bootstrap["bootstrap_diagnostics"])
    )


def test_create_app_is_offline_by_default_and_can_inject_startup_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    calls: list[FilesystemServiceRegistry] = []

    def probe(registry: FilesystemServiceRegistry) -> list[dict]:
        calls.append(registry)
        return [
            {"available": True, "component": "text"},
            {"available": False, "component": "voice", "error_code": "TTS_UNREACHABLE"},
        ]

    monkeypatch.setattr(FilesystemServiceRegistry, "probe_enabled_readiness_services", probe)
    offline_app = mountain_server.create_app(tmp_path / "offline")
    assert offline_app.state.startup_readiness == {"enabled": False, "probed": 0, "available": 0}
    assert calls == []

    app = mountain_server.create_app(tmp_path / "production", startup_readiness_probe=True)
    assert len(calls) == 1
    assert app.state.startup_readiness == {"enabled": True, "probed": 2, "available": 1}
