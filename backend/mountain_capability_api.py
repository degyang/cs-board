"""Native, dynamic capability route for the Mountain composition root."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.application.activation import accepted_v3_gate
from csboard.application.capabilities import CapabilityService


def mountain_capability_router(
    registry: FilesystemServiceRegistry, project_root: Path | str,
) -> APIRouter:
    """Build the capability projection against the composition root's root."""
    router = APIRouter()
    root = Path(project_root).resolve()
    capabilities = CapabilityService(
        registry,
        project_root=root,
        external_stage_gate=lambda: accepted_v3_gate(root),
    )

    @router.get("/api/v1/capabilities")
    async def get_capabilities():
        return capabilities.snapshot()

    return router
