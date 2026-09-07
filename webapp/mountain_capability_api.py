"""Native, dynamic capability route for the Mountain composition root."""

from __future__ import annotations

from fastapi import APIRouter

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.application.capabilities import CapabilityService


def mountain_capability_router(registry: FilesystemServiceRegistry, project_root=None) -> APIRouter:
    router = APIRouter()
    from pathlib import Path
    from csboard.application.activation import accepted_v3_gate
    root = Path(project_root).resolve() if project_root is not None else Path(__file__).resolve().parents[1]
    capabilities = CapabilityService(
        registry, project_root=root,
        external_stage_gate=lambda: accepted_v3_gate(root),
    )

    @router.get("/api/v1/capabilities")
    def get_capabilities():
        return capabilities.snapshot()

    return router
