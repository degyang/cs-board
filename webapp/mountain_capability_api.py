"""Native, dynamic capability route for the Mountain composition root."""

from __future__ import annotations

from fastapi import APIRouter

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.application.capabilities import CapabilityService


def mountain_capability_router(registry: FilesystemServiceRegistry) -> APIRouter:
    router = APIRouter()
    capabilities = CapabilityService(registry)

    @router.get("/api/v1/capabilities")
    def get_capabilities():
        return capabilities.snapshot()

    return router
