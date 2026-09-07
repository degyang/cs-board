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
from csboard.application.service_capabilities import (
    declared_capabilities,
    normalized_capability,
)


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
    # Illustration output is supplied by the accepted external/manual gate,
    # never by an automatically probed image provider.
    "generate-illustrations": (),
}

# Stable bootstrap reason codes, ordered by the first failing prerequisite.
SERVICE_SECRET_MISSING = "SERVICE_SECRET_MISSING"
SERVICE_PROBE_FAILED = "SERVICE_PROBE_FAILED"
# Compatibility names are deliberately aliases, so callers do not obtain a
# second public reason-code vocabulary.
SERVICE_SECRET_NOT_CONFIGURED = SERVICE_SECRET_MISSING
SERVICE_PROBE_UNAVAILABLE = SERVICE_PROBE_FAILED
# Historical public reason code retained for the P3a test contract.  V3
# activation may project a missing pointer as EVIDENCE_MISSING, but must not
# redefine this existing constant to make old consumers silently accept that
# new vocabulary.
REAL_SMOKE_EVIDENCE_REQUIRED = "REAL_SMOKE_EVIDENCE_REQUIRED"
# Legacy test/import compatibility only; P3a does not perform this probe.
NODE_NOT_FOUND = "NODE_NOT_FOUND"
_TOOLCHAIN_COMPONENTS = (
    "node",
    "render-script",
    "lockfile",
    "locked-remotion",
    "remotion-browser",
    "ffmpeg",
    "ffprobe",
)


def _check(component: str, ready: bool, reason_code: str | None = None) -> dict[str, Any]:
    """Return a public-safe diagnostic; never include commands or paths."""
    return {"component": component, "ready": ready, "reason_code": reason_code}




class CapabilityService:
    """Build sanitized availability and P3a bootstrap snapshots without live probes."""

    def __init__(self, registry: FilesystemServiceRegistry, project_root: object | None = None,
                 external_stage_gate: Callable[[], bool] | None = None,
                 toolchain_probe: Callable[[object | None], list[dict[str, Any]]] | None = None,
                 activation_verifier_factory: Callable[[Path, str], Any] | None = None) -> None:
        self._registry = registry
        # Retain the legacy argument for composition-root compatibility.  P3a
        # must not inspect the filesystem or a renderer toolchain through it.
        self._project_root = project_root
        self._external_stage_gate = external_stage_gate
        # The composition root may inject a precomputed, safe probe result for
        # this snapshot.  This service never discovers or starts a renderer.
        self._toolchain_probe = toolchain_probe
        self._activation_verifier_factory = activation_verifier_factory

    def snapshot(self) -> dict[str, Any]:
        providers: dict[str, dict[str, Any]] = {}
        unavailable: list[str] = []
        services_by_capability: dict[str, list[str]] = {}
        services = self._unique_services()
        for service in services:
            status = self._service_status(service)
            providers[service.service_id] = status
            for capability in declared_capabilities(service):
                normalized = normalized_capability(capability)
                services_by_capability.setdefault(normalized, []).append(service.service_id)
            if not status["available"]:
                unavailable.append(service.service_id)

        missing = self._missing_requirements(providers, services_by_capability, WHITEBOARD_STAGE_REQUIREMENTS)
        all_available = not missing
        whiteboard_reason = None if all_available else (
            _EXTERNAL_GATE_CODE if set(missing) == {"image_generation"} else "CAPABILITY_NOT_AVAILABLE"
        )
        bootstrap = self._bootstrap_snapshot(services)
        # Activation re-reads its evidence for every projection.  The safe
        # bootstrap diagnostic is also the current service-prerequisite fingerprint.
        from csboard.application.activation import ActivationVerifier
        safe_fingerprint = self._service_fingerprint(services, bootstrap["bootstrap_diagnostics"])
        root = Path(self._project_root).resolve() if self._project_root is not None else Path(__file__).resolve().parents[2]
        verifier = (self._activation_verifier_factory(root, safe_fingerprint)
                    if self._activation_verifier_factory is not None
                    else ActivationVerifier(root, current_service_fingerprint=safe_fingerprint))
        activation = verifier.verify(bootstrap["bootstrap_ready"])
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
        checks = self._toolchain_checks() + self._bootstrap_service_checks(services)
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

    def _toolchain_checks(self) -> list[dict[str, Any]]:
        """Return injected toolchain diagnostics, failing closed when absent or invalid."""
        try:
            if self._toolchain_probe is None:
                from csboard.runtime.toolchain import bootstrap_diagnostics
                root = Path(self._project_root).resolve() if self._project_root is not None else Path(__file__).resolve().parents[2]
                checks = bootstrap_diagnostics(root)
            else:
                checks = self._toolchain_probe(self._project_root)
            if not isinstance(checks, list) or not all(
                    isinstance(check, dict)
                    and isinstance(check.get("component"), str)
                    and isinstance(check.get("ready"), bool)
                    and (check.get("reason_code") is None or isinstance(check.get("reason_code"), str))
                    for check in checks) or tuple(check["component"] for check in checks) != _TOOLCHAIN_COMPONENTS:
                raise ValueError("invalid toolchain diagnostics")
        except Exception:
            return [_check("node", False, NODE_NOT_FOUND)]
        return [_check(check["component"], check["ready"], check.get("reason_code")) for check in checks]

    def _bootstrap_service_checks(self, services: list[Any]) -> list[dict[str, Any]]:
        by_capability: dict[str, list[Any]] = {}
        for service in services:
            for capability in declared_capabilities(service):
                normalized = normalized_capability(capability)
                by_capability.setdefault(normalized, []).append(service)
        checks: list[dict[str, Any]] = []
        # One deterministic safe diagnostic per capability, not per secret or path.
        # The infographic image stage is external/manual.  Keep image service
        # requirements exclusively in the whiteboard projection above.
        for capability in ("text_generation", "speech_synthesis", "speech_alignment", "media"):
            configured = [service for service in by_capability.get(capability, []) if service.enabled]
            component = f"service-{capability}"
            if not configured or not any(self._has_required_secrets(service) for service in configured):
                checks.append(_check(component, False, SERVICE_SECRET_MISSING))
            elif not any(self._cached_probe_available(service.service_id) for service in configured):
                checks.append(_check(component, False, SERVICE_PROBE_FAILED))
            else:
                checks.append(_check(component, True))
        return checks

    def _service_fingerprint(self, services: list[Any], diagnostics: list[dict[str, Any]]) -> str:
        """Bind activation to service identity/configuration without exposing either.

        Readiness alone cannot distinguish a replacement service from the
        accepted one.  Only this digest leaves the process; secret values are
        represented solely by their availability bit.
        """
        records = []
        for service in sorted(services, key=lambda item: item.service_id):
            records.append({
                "service_id": service.service_id,
                "revision": service.revision,
                "capability": service.capability,
                "adapter_type": service.adapter_type,
                "endpoint": service.endpoint,
                "model": service.model,
                "enabled": service.enabled,
                "priority": service.priority,
                "is_default": service.is_default,
                "config": self._safe_config(service.config),
                "required_secrets": sorted(service.required_secrets),
                "optional_secrets": sorted(service.optional_secrets),
                "required_secrets_ready": self._has_required_secrets(service),
                "probe": self._safe_probe(service.service_id),
            })
        payload = {"diagnostics": diagnostics, "services": records}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def _safe_config(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): ("<configured>" if any(token in str(key).lower().replace("_", "") for token in ("secret", "token", "password", "credential", "apikey", "authorization")) else CapabilityService._safe_config(item)) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
        if isinstance(value, list):
            return [CapabilityService._safe_config(item) for item in value]
        return value if isinstance(value, (str, int, float, bool, type(None))) else str(value)

    def _safe_probe(self, service_id: str) -> dict[str, Any] | None:
        try:
            probe = self._registry.get_cached_probe(service_id)
            if not isinstance(probe, dict):
                return None
            return {"available": bool(probe.get("available", False)), "error_code": probe.get("error_code") if isinstance(probe.get("error_code"), str) else None}
        except Exception:
            return None

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
