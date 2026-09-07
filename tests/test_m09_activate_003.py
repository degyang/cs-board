"""Regression coverage for M09's multi-capability activation boundary."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry, _probe_cache
from csboard.adapters.provider_factory import ProviderFactory
from csboard.adapters.secrets.secret_store import PlaintextSecretStore
from csboard.application.capabilities import CapabilityService
from csboard.application.service_capabilities import declared_capabilities
from csboard.application.service_resolver import ServiceResolver
from csboard.domain.errors import DomainError
from csboard.domain.service_definition import ServiceDefinition


TOOLCHAIN = ("node", "render-script", "lockfile", "locked-remotion", "remotion-browser", "ffmpeg", "ffprobe")


def _ready_toolchain(_root: object) -> list[dict[str, object]]:
    return [{"component": component, "ready": True, "reason_code": None} for component in TOOLCHAIN]


def _registry(root: Path) -> tuple[FilesystemServiceRegistry, PlaintextSecretStore]:
    _probe_cache.clear()
    store = PlaintextSecretStore(root / ".secrets")
    return FilesystemServiceRegistry(root, store), store


def _add(registry: FilesystemServiceRegistry, service_id: str, capability: str, *, config: dict | None = None,
         adapter_type: str = "local_process", required_secrets: list[str] | None = None) -> None:
    registry.create_service(ServiceDefinition(
        service_id=service_id, display_name=service_id, capability=capability,
        adapter_type=adapter_type, config=config or {}, required_secrets=required_secrets or [],
    ))
    _probe_cache[service_id] = ({"available": True, "error_code": None}, time.monotonic())


def _add_ready_infographic_services(registry: FilesystemServiceRegistry) -> None:
    _add(registry, "codeplan", "audio_generation", config={"capabilities": ["text_generation"]},
         adapter_type="openai_compatible", required_secrets=["api_key"])
    registry.set_secret("codeplan", "api_key", "fixture-key")
    _add(registry, "alignment", "speech_alignment")
    _add(registry, "media", "media")
    _add(registry, "renderer", "rendering")


def test_audio_primary_text_secondary_is_ready_for_bootstrap_resolver_and_text_adapter(tmp_path: Path):
    registry, store = _registry(tmp_path)
    _add_ready_infographic_services(registry)
    capabilities = CapabilityService(registry, external_stage_gate=lambda: True, toolchain_probe=_ready_toolchain)

    bootstrap = capabilities._bootstrap_snapshot(capabilities._unique_services())
    text_check = next(check for check in bootstrap["bootstrap_diagnostics"] if check["component"] == "service-text_generation")
    resolved = ServiceResolver(registry).resolve_text_model()
    adapter = ProviderFactory(tmp_path, secret_store=store, is_encrypted=False).create_adapter(resolved)

    assert bootstrap["bootstrap_ready"] is True
    assert text_check["ready"] is True
    assert resolved.service_id == "codeplan"
    assert resolved.capability == "text_generation"
    assert adapter.__class__.__name__ == "OpenAITextAdapter"


def test_infographic_uses_external_gate_without_an_image_service_but_whiteboard_does_not(tmp_path: Path):
    registry, _store = _registry(tmp_path)
    _add_ready_infographic_services(registry)

    open_gate = CapabilityService(registry, external_stage_gate=lambda: True, toolchain_probe=_ready_toolchain)
    closed_gate = CapabilityService(registry, external_stage_gate=lambda: False, toolchain_probe=_ready_toolchain)
    snapshot = open_gate.snapshot()
    infographic = next(item for item in snapshot["items"] if item["engine"] == "infographic-remotion")
    whiteboard = next(item for item in snapshot["items"] if item["engine"] == "whiteboard" and item["visual_source"] == "preset")

    assert infographic["bootstrap_ready"] is True
    assert whiteboard["supported"] is False
    assert whiteboard["reason_code"] == "EXTERNAL_STAGE_GATE_REQUIRED"
    assert closed_gate._bootstrap_snapshot(closed_gate._unique_services())["bootstrap_reason_code"] == "EXTERNAL_STAGE_BLOCKED"


@pytest.mark.parametrize("secondary", [None, "text_generation", [None, "", 4], []])
def test_invalid_secondary_capabilities_do_not_turn_tts_into_a_text_model(tmp_path: Path, secondary: object):
    registry, _store = _registry(tmp_path)
    _add(registry, "tts-only", "audio_generation", config={"capabilities": secondary})

    with pytest.raises(DomainError) as error:
        ServiceResolver(registry).resolve_text_model()
    assert error.value.code == "CAPABILITY_NOT_AVAILABLE"
    assert declared_capabilities(registry.get_service("tts-only")) == ("audio_generation",)


def test_secondary_capabilities_are_string_only_and_de_duplicated(tmp_path: Path):
    registry, _store = _registry(tmp_path)
    _add(registry, "codeplan", "audio_generation", config={
        "capabilities": ["text_generation", "text_generation", "", 7, None, " speech_alignment "],
        "unrelated": "text_generation",
    })

    assert declared_capabilities(registry.get_service("codeplan")) == (
        "audio_generation", "text_generation", "speech_alignment",
    )
