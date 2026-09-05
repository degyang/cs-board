"""Read-only, fail-closed capability and bootstrap projections.

The infographic bootstrap report deliberately is *not* an activation decision.
Only the later evidence-activation package may change ``supported`` to true.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry


_EXTERNAL_STAGE = "generate-illustrations"
_EXTERNAL_GATE_CODE = "EXTERNAL_STAGE_GATE_REQUIRED"

WHITEBOARD_STAGE_REQUIREMENTS = {
    "generate-visual-anchors": ("text_generation",),
    "clone-voice": ("speech_synthesis", "speech_alignment", "media"),
    "plan-storyboard": ("text_generation",),
    "generate-illustrations": ("image_generation",),
    "render-visuals": ("rendering",),
    "compose-video": ("media",),
}
INFOGRAPHIC_STAGE_REQUIREMENTS = {
    "generate-visual-anchors": ("text_generation",),
    "clone-voice": ("speech_synthesis", "speech_alignment", "media"),
    "plan-storyboard": ("text_generation",),
    "generate-illustrations": ("image_generation",),
}

# Stable bootstrap reason codes, ordered by the first failing prerequisite.
SERVICE_SECRET_MISSING = "SERVICE_SECRET_MISSING"
SERVICE_PROBE_FAILED = "SERVICE_PROBE_FAILED"
# Compatibility names are deliberately aliases, so callers do not obtain a
# second public reason-code vocabulary.
SERVICE_SECRET_NOT_CONFIGURED = SERVICE_SECRET_MISSING
SERVICE_PROBE_UNAVAILABLE = SERVICE_PROBE_FAILED
REAL_SMOKE_EVIDENCE_REQUIRED = "REAL_SMOKE_EVIDENCE_REQUIRED"
# Legacy test/import compatibility only; P3a does not perform this probe.
NODE_NOT_FOUND = "NODE_NOT_FOUND"


def _check(component: str, ready: bool, reason_code: str | None = None) -> dict[str, Any]:
    """Return a public-safe diagnostic; never include commands or paths."""
    return {"component": component, "ready": ready, "reason_code": reason_code}




class CapabilityService:
    """Build sanitized availability and P3a bootstrap snapshots without probes."""

    def __init__(self, registry: FilesystemServiceRegistry, project_root: object | None = None,
                 external_stage_gate: Callable[[], bool] | None = None) -> None:
        self._registry = registry
        # Retain the legacy argument for composition-root compatibility.  P3a
        # must not inspect the filesystem or a renderer toolchain through it.
        self._project_root = project_root
        self._external_stage_gate = external_stage_gate

    def snapshot(self) -> dict[str, Any]:
        providers: dict[str, dict[str, Any]] = {}
        unavailable: list[str] = []
        services_by_capability: dict[str, list[str]] = {}
        services = self._unique_services()
        for service in services:
            status = self._service_status(service)
            providers[service.service_id] = status
            capability = self._normalized_capability(service.capability)
            services_by_capability.setdefault(capability, []).append(service.service_id)
            if not status["available"]:
                unavailable.append(service.service_id)

        missing = self._missing_requirements(providers, services_by_capability, WHITEBOARD_STAGE_REQUIREMENTS)
        all_available = not missing
        whiteboard_reason = None if all_available else (
            _EXTERNAL_GATE_CODE if set(missing) == {"image_generation"} else "CAPABILITY_NOT_AVAILABLE"
        )
        bootstrap = self._bootstrap_snapshot(services)
        # P3b intentionally re-reads P3a plus evidence for every projection.
        from csboard.application.activation import ActivationVerifier
        safe_fingerprint = hashlib.sha256(json.dumps(bootstrap["bootstrap_diagnostics"], sort_keys=True).encode()).hexdigest()
        activation = ActivationVerifier(Path(__file__).resolve().parents[2], current_service_fingerprint=safe_fingerprint).verify(bootstrap["bootstrap_ready"])
        infographic_reason = activation["reason_code"]

        return {
            "items": [
                {"engine": "whiteboard", "visual_source": "preset", "supported": all_available,
                 "pipeline_id": "mountain-av-v1", "reason_code": whiteboard_reason},
                {"engine": "whiteboard", "visual_source": "custom-reference", "supported": False,
                 "pipeline_id": "mountain-av-v1", "reason_code": "CAPABILITY_NOT_AVAILABLE"},
                {"engine": "infographic-remotion", "visual_source": "preset", "supported": False,
                 "pipeline_id": "mountain-av-v1", "reason_code": infographic_reason, **bootstrap,
                 "activation_diagnostics": activation["diagnostics"], "supported": activation["supported"]},
            ],
            "providers": {"all_available": all_available, "providers": providers, "unavailable": unavailable},
        }

    def _bootstrap_snapshot(self, services: list[Any]) -> dict[str, Any]:
        checks = self._bootstrap_service_checks(services)
        try:
            external_ready = bool(self._external_stage_gate and self._external_stage_gate())
        except Exception:
            external_ready = False
        checks.append(_check("external-stage-gate", external_ready, "EXTERNAL_STAGE_BLOCKED"))
        first_failure = next((check for check in checks if not check["ready"]), None)
        return {
            "bootstrap_ready": first_failure is None,
            "bootstrap_checked_at": datetime.now(UTC).isoformat(),
            "bootstrap_reason_code": None if first_failure is None else first_failure["reason_code"],
            "bootstrap_diagnostics": checks,
        }

    def _bootstrap_service_checks(self, services: list[Any]) -> list[dict[str, Any]]:
        by_capability: dict[str, list[Any]] = {}
        for service in services:
            by_capability.setdefault(self._normalized_capability(service.capability), []).append(service)
        checks: list[dict[str, Any]] = []
        # One deterministic safe diagnostic per capability, not per secret or path.
        for capability in ("text_generation", "speech_synthesis", "speech_alignment", "image_generation", "media"):
            configured = [service for service in by_capability.get(capability, []) if service.enabled]
            component = f"service-{capability}"
            if not configured or not any(self._has_required_secrets(service) for service in configured):
                checks.append(_check(component, False, SERVICE_SECRET_MISSING))
            elif not any(self._cached_probe_available(service.service_id) for service in configured):
                checks.append(_check(component, False, SERVICE_PROBE_FAILED))
            else:
                checks.append(_check(component, True))
        return checks

    def _has_required_secrets(self, service: Any) -> bool:
        try:
            return bool(self._registry.has_required_secrets(service))
        except Exception:
            return False

    def _cached_probe_available(self, service_id: str) -> bool:
        try:
            probe = self._registry.get_cached_probe(service_id)
        except Exception:
            return False
        return bool(probe and probe.get("available", False))

    def _unique_services(self) -> list[Any]:
        seen: set[str] = set()
        return [service for service in self._registry.list_services()
                if not (service.service_id in seen or seen.add(service.service_id))]

    @staticmethod
    def _normalized_capability(capability: str) -> str:
        return "speech_synthesis" if capability == "audio_generation" else capability

    @staticmethod
    def _missing_requirements(providers: dict[str, dict[str, Any]], services_by_capability: dict[str, list[str]],
                              requirements: dict[str, tuple[str, ...]]) -> set[str]:
        missing: set[str] = set()
        for stage, capabilities in requirements.items():
            for capability in capabilities:
                if stage == _EXTERNAL_STAGE:
                    missing.add(capability)
                elif not any(providers[service_id]["available"] for service_id in services_by_capability.get(capability, [])):
                    missing.add(capability)
        return missing

    def _service_status(self, service: Any) -> dict[str, Any]:
        if not service.enabled:
            return self._status(service.service_id, False, "SERVICE_DISABLED")
        if not self._has_required_secrets(service):
            return self._status(service.service_id, False, "SECRET_NOT_CONFIGURED")
        if service.capability == "image_generation":
            return self._status(service.service_id, False, _EXTERNAL_GATE_CODE)
        try:
            probe = self._registry.get_cached_probe(service.service_id)
        except Exception:
            return self._status(service.service_id, False, SERVICE_PROBE_FAILED)
        if probe is None:
            return self._status(service.service_id, False, "NOT_PROBED")
        return self._status(service.service_id, bool(probe.get("available", False)), probe.get("error_code"))

    @staticmethod
    def _status(service_id: str, available: bool, error_code: str | None) -> dict[str, Any]:
        return {"available": available, "component": service_id, "error_code": error_code, "suggestion": None}
