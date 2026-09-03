"""Read-only capability projection for the native Mountain API."""

from __future__ import annotations

from typing import Any

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry


# The illustration work order deliberately has no executable native command.
# A configured image service must not make the standard whiteboard flow look
# executable until its external candidate gate exists.
_EXTERNAL_STAGE = "generate-illustrations"
_EXTERNAL_GATE_CODE = "EXTERNAL_STAGE_GATE_REQUIRED"

# This is intentionally not inferred from the one-capability stage resolver
# map: clone-voice builds three adapters in its executor. Keeping the full
# requirements here makes the read-only UI projection match execution.
WHITEBOARD_STAGE_REQUIREMENTS = {
    "generate-visual-anchors": ("text_generation",),
    "clone-voice": ("speech_synthesis", "speech_alignment", "media"),
    "plan-storyboard": ("text_generation",),
    "generate-illustrations": ("image_generation",),
    "render-visuals": ("rendering",),
    "compose-video": ("media",),
}


class CapabilityService:
    """Build a sanitized availability snapshot without probing services."""

    def __init__(self, registry: FilesystemServiceRegistry) -> None:
        self._registry = registry

    def snapshot(self) -> dict[str, Any]:
        providers: dict[str, dict[str, Any]] = {}
        unavailable: list[str] = []
        services_by_capability: dict[str, list[str]] = {}

        for service in self._registry.list_services():
            status = self._service_status(service)
            providers[service.service_id] = status
            services_by_capability.setdefault(service.capability, []).append(service.service_id)
            if not status["available"]:
                unavailable.append(service.service_id)

        missing = self._missing_requirements(providers, services_by_capability)
        all_available = not missing
        reason_code = None if all_available else (
            _EXTERNAL_GATE_CODE if set(missing) == {"image_generation"}
            else "CAPABILITY_NOT_AVAILABLE"
        )
        return {
            "items": [
                {
                    "engine": "whiteboard",
                    "visual_source": "preset",
                    "supported": all_available,
                    "pipeline_id": "mountain-av-v1",
                    "reason_code": reason_code,
                },
                {
                    "engine": "whiteboard",
                    "visual_source": "custom-reference",
                    "supported": False,
                    "pipeline_id": "mountain-av-v1",
                    "reason_code": "CAPABILITY_NOT_AVAILABLE",
                },
                {
                    "engine": "infographic-remotion",
                    "visual_source": "preset",
                    "supported": False,
                    "pipeline_id": "mountain-av-v1",
                    "reason_code": "CAPABILITY_NOT_AVAILABLE",
                },
            ],
            "providers": {
                "all_available": all_available,
                "providers": providers,
                "unavailable": unavailable,
            },
        }

    @staticmethod
    def _missing_requirements(
        providers: dict[str, dict[str, Any]],
        services_by_capability: dict[str, list[str]],
    ) -> set[str]:
        missing = set()
        for stage, capabilities in WHITEBOARD_STAGE_REQUIREMENTS.items():
            for capability in capabilities:
                if stage == _EXTERNAL_STAGE:
                    missing.add(capability)
                elif not any(providers[service_id]["available"]
                             for service_id in services_by_capability.get(capability, [])):
                    missing.add(capability)
        return missing

    def _service_status(self, service: Any) -> dict[str, Any]:
        if not service.enabled:
            return self._status(service.service_id, False, "SERVICE_DISABLED")
        if not self._registry.has_required_secrets(service):
            return self._status(service.service_id, False, "SECRET_NOT_CONFIGURED")
        if service.capability == "image_generation":
            return self._status(service.service_id, False, _EXTERNAL_GATE_CODE)

        probe = self._registry.get_cached_probe(service.service_id)
        if probe is None:
            return self._status(service.service_id, False, "NOT_PROBED")
        return self._status(
            service.service_id,
            bool(probe.get("available", False)),
            probe.get("error_code"),
        )

    @staticmethod
    def _status(service_id: str, available: bool, error_code: str | None) -> dict[str, Any]:
        return {
            "available": available,
            "component": service_id,
            "error_code": error_code,
            "suggestion": None,
        }
