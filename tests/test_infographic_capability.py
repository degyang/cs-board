"""P3a bootstrap diagnostics stay fail-closed without real rendering."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry, _probe_cache
from csboard.adapters.secrets.secret_store import PlaintextSecretStore
from csboard.application.capabilities import REAL_SMOKE_EVIDENCE_REQUIRED, SERVICE_PROBE_UNAVAILABLE, CapabilityService
from csboard.domain.service_definition import ServiceDefinition


def _registry(tmp_path: Path) -> FilesystemServiceRegistry:
    _probe_cache.clear()
    return FilesystemServiceRegistry(tmp_path, PlaintextSecretStore(tmp_path / ".secrets"))


def _service(service_id: str, capability: str) -> ServiceDefinition:
    return ServiceDefinition(service_id=service_id, display_name=service_id, capability=capability,
                             adapter_type="local_process", required_secrets=[])


NONRENDERER_CAPABILITIES = (
    "text_generation", "speech_synthesis", "speech_alignment", "image_generation", "media",
)


def _available_services(registry: FilesystemServiceRegistry, *, omit: str | None = None) -> None:
    for suffix, capability in (("words", "text_generation"), ("voice", "speech_synthesis"),
                               ("align", "speech_alignment"), ("image", "image_generation"),
                               ("draw", "rendering"), ("mux", "media")):
        if capability == omit:
            continue
        service_id = f"custom-{suffix}"
        registry.create_service(_service(service_id, capability))
        _probe_cache[service_id] = ({"available": True, "error_code": None}, time.monotonic())


def _item(snapshot: dict) -> dict:
    return next(item for item in snapshot["items"] if item["engine"] == "infographic-remotion")


def test_bootstrap_reports_multiple_missing_items_but_one_stable_reason(tmp_path: Path):
    item = _item(CapabilityService(_registry(tmp_path), project_root=tmp_path).snapshot())
    assert item["bootstrap_ready"] is False
    assert item["bootstrap_reason_code"] == "SERVICE_SECRET_MISSING"


def test_bootstrap_ready_still_requires_real_smoke_evidence(tmp_path: Path):
    registry = _registry(tmp_path)
    _available_services(registry)
    item = _item(CapabilityService(registry, project_root=tmp_path, external_stage_gate=lambda: True).snapshot())
    assert item["bootstrap_ready"] is True
    # Production P6 evidence has no independently signed current-service
    # fingerprint, so P3b remains fail-closed despite ready bootstrap.
    assert item["supported"] is False
    assert item["reason_code"] == "SERVICE_PROBE_CHANGED"
    assert "bootstrap_checked_at" in item
    assert all("/" not in str(value) for check in item["bootstrap_diagnostics"] for value in check.values())


def test_service_probe_failure_is_fail_closed(tmp_path: Path):
    registry = _registry(tmp_path)
    _available_services(registry)
    _probe_cache["custom-align"] = ({"available": False, "error_code": "PROBE_FAILED"}, time.monotonic())
    item = _item(CapabilityService(registry, project_root=tmp_path).snapshot())
    assert item["bootstrap_ready"] is False
    assert item["bootstrap_reason_code"] == SERVICE_PROBE_UNAVAILABLE
    assert item["supported"] is False


def test_whiteboard_projection_does_not_depend_on_bootstrap(tmp_path: Path):
    registry = _registry(tmp_path)
    _available_services(registry)
    snapshot = CapabilityService(registry, project_root=tmp_path).snapshot()
    whiteboard = next(item for item in snapshot["items"] if item["engine"] == "whiteboard" and item["visual_source"] == "preset")
    assert whiteboard["reason_code"] == "EXTERNAL_STAGE_GATE_REQUIRED"


@pytest.mark.parametrize(
    "gate",
    [None, lambda: False, lambda: (_ for _ in ()).throw(RuntimeError("/operator-secret"))],
    ids=("missing", "false", "exception"),
)
def test_external_gate_missing_false_or_exception_is_fail_closed(tmp_path: Path, gate):
    registry = _registry(tmp_path); _available_services(registry)
    item = _item(CapabilityService(registry, external_stage_gate=gate).snapshot())
    assert item["bootstrap_ready"] is False
    assert item["bootstrap_reason_code"] == "EXTERNAL_STAGE_BLOCKED"


@pytest.mark.parametrize("capability", NONRENDERER_CAPABILITIES)
def test_each_nonrenderer_capability_missing_is_fail_closed(tmp_path: Path, capability: str):
    registry = _registry(tmp_path)
    _available_services(registry, omit=capability)
    item = _item(CapabilityService(registry, external_stage_gate=lambda: True).snapshot())
    check = next(check for check in item["bootstrap_diagnostics"]
                 if check["component"] == f"service-{capability}")
    assert item["bootstrap_ready"] is False
    assert check == {"component": f"service-{capability}", "ready": False,
                     "reason_code": "SERVICE_SECRET_MISSING"}


@pytest.mark.parametrize("capability", NONRENDERER_CAPABILITIES)
def test_each_nonrenderer_capability_secret_failure_is_fail_closed(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capability: str):
    registry = _registry(tmp_path)
    _available_services(registry)
    original = registry.has_required_secrets
    monkeypatch.setattr(registry, "has_required_secrets",
                        lambda service: False if service.capability == capability else original(service))
    item = _item(CapabilityService(registry, external_stage_gate=lambda: True).snapshot())
    check = next(check for check in item["bootstrap_diagnostics"]
                 if check["component"] == f"service-{capability}")
    assert item["bootstrap_ready"] is False
    assert check["reason_code"] == "SERVICE_SECRET_MISSING"


@pytest.mark.parametrize("capability", NONRENDERER_CAPABILITIES)
def test_each_nonrenderer_capability_probe_failure_is_fail_closed(tmp_path: Path, capability: str):
    registry = _registry(tmp_path)
    _available_services(registry)
    service = next(service for service in registry.list_services() if service.capability == capability)
    _probe_cache[service.service_id] = ({"available": False, "error_code": "PROBE_FAILED"}, time.monotonic())
    item = _item(CapabilityService(registry, external_stage_gate=lambda: True).snapshot())
    check = next(check for check in item["bootstrap_diagnostics"]
                 if check["component"] == f"service-{capability}")
    assert item["bootstrap_ready"] is False
    assert check["reason_code"] == SERVICE_PROBE_UNAVAILABLE


def test_secret_and_probe_exceptions_fail_closed_and_safe(tmp_path: Path, monkeypatch):
    registry = _registry(tmp_path); _available_services(registry)
    monkeypatch.setattr(registry, "has_required_secrets", lambda _service: (_ for _ in ()).throw(RuntimeError("/secret-value")))
    item = _item(CapabilityService(registry, external_stage_gate=lambda: True).snapshot())
    assert item["bootstrap_reason_code"] == "SERVICE_SECRET_MISSING"
    monkeypatch.setattr(registry, "has_required_secrets", lambda _service: True)
    monkeypatch.setattr(registry, "get_cached_probe", lambda _id: (_ for _ in ()).throw(RuntimeError("/probe-path")))
    item = _item(CapabilityService(registry, external_stage_gate=lambda: True).snapshot())
    assert item["bootstrap_reason_code"] == SERVICE_PROBE_UNAVAILABLE
    assert "/" not in str(item["bootstrap_diagnostics"]) and "secret-value" not in str(item["bootstrap_diagnostics"])


def test_multi_missing_diagnostics_are_complete_ordered_and_utc(tmp_path: Path):
    item = _item(CapabilityService(_registry(tmp_path)).snapshot())
    checks = item["bootstrap_diagnostics"]
    assert [check["component"] for check in checks] == [
        "service-text_generation", "service-speech_synthesis", "service-speech_alignment", "service-image_generation", "service-media", "external-stage-gate",
    ]
    assert item["bootstrap_reason_code"] == checks[0]["reason_code"]
    checked_at = datetime.fromisoformat(item["bootstrap_checked_at"])
    assert checked_at.utcoffset() == UTC.utcoffset(checked_at)
    # Public diagnostics expose reason *codes*, never the sensitive exception
    # text, a filesystem path, or an individual secret name/value.
    diagnostic_text = str(checks)
    assert "/" not in diagnostic_text
    assert "top-secret" not in diagnostic_text
    assert all(set(check) == {"component", "ready", "reason_code"} for check in checks)
