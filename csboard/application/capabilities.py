"""Read-only capability projection for the native Mountain API."""

from __future__ import annotations

from typing import Any

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.application.service_resolver import STAGE_CAPABILITY_MAP
from csboard.domain.execution_plan import CANONICAL_STAGES


# The illustration work order deliberately has no executable native command.
# A configured image service must not make the standard whiteboard flow look
# executable until its external candidate gate exists.
_EXTERNAL_STAGE = "generate-illustrations"
_EXTERNAL_GATE_CODE = "EXTERNAL_STAGE_GATE_REQUIRED"


class CapabilityService:
    """Build a sanitized availability snapshot without probing services."""

    def __init__(self, registry: FilesystemServiceRegistry) -> None:
        self._registry = registry

    def snapshot(self) -> dict[str, Any]:
        providers: dict[str, dict[str, Any]] = {}
        unavailable: list[str] = []
        capability_status: dict[str, bool] = {}

        for service in self._registry.list_services():
            status = self._service_status(service)
            providers[service.service_id] = status
            if not status["available"]:
                unavailable.append(service.service_id)

        for stage in CANONICAL_STAGES:
            capability = STAGE_CAPABILITY_MAP[stage]
            capability_status[capability] = self._capability_available(stage, providers)

        all_available = all(
            capability_status[STAGE_CAPABILITY_MAP[stage]]
            for stage in CANONICAL_STAGES
        )
        return {
            "items": [
                {
                    "engine": "whiteboard",
                    "visual_source": "preset",
                    "supported": all_available,
                    "pipeline_id": "mountain-av-v1",
                    "reason_code": None if all_available else "CAPABILITY_NOT_AVAILABLE",
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

    def _capability_available(self, stage: str, providers: dict[str, dict[str, Any]]) -> bool:
        if stage == _EXTERNAL_STAGE:
            return False
        capability = STAGE_CAPABILITY_MAP[stage]
        return any(
            status["available"]
            for service, status in providers.items()
            if self._registry.get_service(service).capability == capability
        )

    def _service_status(self, service: Any) -> dict[str, Any]:
        if not service.enabled:
            return self._status(service.service_id, False, "SERVICE_DISABLED")
        if not self._registry.has_required_secrets(service):
            return self._status(service.service_id, False, "SECRET_NOT_CONFIGURED")
        if service.capability == STAGE_CAPABILITY_MAP[_EXTERNAL_STAGE]:
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
