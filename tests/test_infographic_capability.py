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
    "text_generation", "speech_synthesis", "speech_alignment", "media",
)
TOOLCHAIN_COMPONENTS = (
    ("node", "NODE_NOT_FOUND"),
    ("render-script", "RENDER_SCRIPT_MISSING"),
    ("lockfile", "LOCKFILE_INVALID"),
    ("locked-remotion", "REMOTION_NOT_INSTALLED"),
    ("remotion-browser", "BROWSER_UNAVAILABLE"),
    ("ffmpeg", "FFMPEG_NOT_FOUND"),
    ("ffprobe", "FFPROBE_NOT_FOUND"),
)


def _ready_toolchain(_root: Path) -> list[dict[str, object]]:
    return [{"component": component, "ready": True, "reason_code": None}
            for component, _code in TOOLCHAIN_COMPONENTS]


def _cap(registry: FilesystemServiceRegistry, *, project_root: Path | None = None,
         external_stage_gate=None, toolchain_probe=_ready_toolchain) -> CapabilityService:
    return CapabilityService(registry, project_root=project_root,
                             external_stage_gate=external_stage_gate,
                             toolchain_probe=toolchain_probe)


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
    item = _item(_cap(_registry(tmp_path), project_root=tmp_path).snapshot())
    assert item["bootstrap_ready"] is False
    assert item["bootstrap_reason_code"] == "SERVICE_SECRET_MISSING"


def test_bootstrap_ready_still_requires_real_smoke_evidence(tmp_path: Path):
    registry = _registry(tmp_path)
    _available_services(registry)
    item = _item(_cap(registry, project_root=tmp_path, external_stage_gate=lambda: True).snapshot())
    assert item["bootstrap_ready"] is True
    # P3a deliberately does not read P6 evidence, so public activation stays
    # fail-closed even with every bootstrap prerequisite present.
    assert item["supported"] is False
    # The legacy public constant retains its historical value.  The new V3
    # verifier is permitted to project a missing activation pointer using its
    # distinct, current reason code.
    assert REAL_SMOKE_EVIDENCE_REQUIRED == "REAL_SMOKE_EVIDENCE_REQUIRED"
    assert item["reason_code"] == "EVIDENCE_MISSING"
    assert "bootstrap_checked_at" in item
    assert all("/" not in str(value) for check in item["bootstrap_diagnostics"] for value in check.values())


def test_service_probe_failure_is_fail_closed(tmp_path: Path):
    registry = _registry(tmp_path)
    _available_services(registry)
    _probe_cache["custom-align"] = ({"available": False, "error_code": "PROBE_FAILED"}, time.monotonic())
    item = _item(_cap(registry, project_root=tmp_path).snapshot())
    assert item["bootstrap_ready"] is False
    assert item["bootstrap_reason_code"] == SERVICE_PROBE_UNAVAILABLE
    assert item["supported"] is False


def test_whiteboard_projection_does_not_depend_on_bootstrap(tmp_path: Path):
    registry = _registry(tmp_path)
    _available_services(registry)
    snapshot = _cap(registry, project_root=tmp_path).snapshot()
    whiteboard = next(item for item in snapshot["items"] if item["engine"] == "whiteboard" and item["visual_source"] == "preset")
    assert whiteboard["reason_code"] == "EXTERNAL_STAGE_GATE_REQUIRED"


@pytest.mark.parametrize(
    "gate",
    [None, lambda: False, lambda: (_ for _ in ()).throw(RuntimeError("/operator-secret"))],
    ids=("missing", "false", "exception"),
)
def test_external_gate_missing_false_or_exception_is_fail_closed(tmp_path: Path, gate):
    registry = _registry(tmp_path); _available_services(registry)
    item = _item(_cap(registry, external_stage_gate=gate).snapshot())
    assert item["bootstrap_ready"] is False
    assert item["bootstrap_reason_code"] == "EXTERNAL_STAGE_BLOCKED"


@pytest.mark.parametrize("capability", NONRENDERER_CAPABILITIES)
def test_each_nonrenderer_capability_missing_is_fail_closed(tmp_path: Path, capability: str):
    registry = _registry(tmp_path)
    _available_services(registry, omit=capability)
    item = _item(_cap(registry, external_stage_gate=lambda: True).snapshot())
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
    item = _item(_cap(registry, external_stage_gate=lambda: True).snapshot())
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
    item = _item(_cap(registry, external_stage_gate=lambda: True).snapshot())
    check = next(check for check in item["bootstrap_diagnostics"]
                 if check["component"] == f"service-{capability}")
    assert item["bootstrap_ready"] is False
    assert check["reason_code"] == SERVICE_PROBE_UNAVAILABLE


def test_secret_and_probe_exceptions_fail_closed_and_safe(tmp_path: Path, monkeypatch):
    registry = _registry(tmp_path); _available_services(registry)
    monkeypatch.setattr(registry, "has_required_secrets", lambda _service: (_ for _ in ()).throw(RuntimeError("/secret-value")))
    item = _item(_cap(registry, external_stage_gate=lambda: True).snapshot())
    assert item["bootstrap_reason_code"] == "SERVICE_SECRET_MISSING"
    monkeypatch.setattr(registry, "has_required_secrets", lambda _service: True)
    monkeypatch.setattr(registry, "get_cached_probe", lambda _id: (_ for _ in ()).throw(RuntimeError("/probe-path")))
    item = _item(_cap(registry, external_stage_gate=lambda: True).snapshot())
    assert item["bootstrap_reason_code"] == SERVICE_PROBE_UNAVAILABLE
    assert "/" not in str(item["bootstrap_diagnostics"]) and "secret-value" not in str(item["bootstrap_diagnostics"])


def test_multi_missing_diagnostics_are_complete_ordered_and_utc(tmp_path: Path):
    item = _item(_cap(_registry(tmp_path)).snapshot())
    checks = item["bootstrap_diagnostics"]
    assert [check["component"] for check in checks] == [
        *(component for component, _code in TOOLCHAIN_COMPONENTS),
        "service-text_generation", "service-speech_synthesis", "service-speech_alignment", "service-media", "external-stage-gate",
    ]
    assert item["bootstrap_reason_code"] == next(check["reason_code"] for check in checks if not check["ready"])
    checked_at = datetime.fromisoformat(item["bootstrap_checked_at"])
    assert checked_at.utcoffset() == UTC.utcoffset(checked_at)
    # Public diagnostics expose reason *codes*, never the sensitive exception
    # text, a filesystem path, or an individual secret name/value.
    diagnostic_text = str(checks)
    assert "/" not in diagnostic_text
    assert "top-secret" not in diagnostic_text
    assert all(set(check) == {"component", "ready", "reason_code"} for check in checks)


@pytest.mark.parametrize("missing_component, reason_code", TOOLCHAIN_COMPONENTS)
def test_each_toolchain_prerequisite_is_fail_closed(tmp_path: Path, missing_component: str, reason_code: str):
    registry = _registry(tmp_path)

    def probe(_root: Path) -> list[dict[str, object]]:
        return [{"component": component, "ready": component != missing_component,
                 "reason_code": None if component != missing_component else code}
                for component, code in TOOLCHAIN_COMPONENTS]

    item = _item(_cap(registry, external_stage_gate=lambda: True, toolchain_probe=probe).snapshot())
    assert item["bootstrap_ready"] is False
    assert item["bootstrap_reason_code"] == reason_code


def test_toolchain_exception_is_fail_closed_and_uses_first_reason(tmp_path: Path):
    item = _item(_cap(_registry(tmp_path), external_stage_gate=lambda: True,
                     toolchain_probe=lambda _root: (_ for _ in ()).throw(RuntimeError("/private"))).snapshot())
    assert item["bootstrap_ready"] is False
    assert item["bootstrap_reason_code"] == "NODE_NOT_FOUND"
    assert "/private" not in str(item["bootstrap_diagnostics"])


def test_service_fingerprint_binds_identity_and_safe_configuration(tmp_path: Path):
    registry = _registry(tmp_path)
    _available_services(registry)
    service = _cap(registry, external_stage_gate=lambda: True)
    before_services = service._unique_services()
    before = service._service_fingerprint(
        before_services, service._bootstrap_snapshot(before_services)["bootstrap_diagnostics"],
    )

    # The replacement remains equally ready, but its identity/configuration
    # changes.  Activation must not silently accept the old fingerprint.
    registry.update_service("custom-words", {"endpoint": "https://replacement.invalid", "model": "replacement-model"})
    after_services = service._unique_services()
    after_bootstrap = service._bootstrap_snapshot(after_services)
    after = service._service_fingerprint(after_services, after_bootstrap["bootstrap_diagnostics"])

    assert after_bootstrap["bootstrap_ready"] is True
    assert before != after
