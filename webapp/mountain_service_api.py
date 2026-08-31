"""Mountain Service API — /api/v1/services 路由。

动态 Service API，不依赖 PROVIDER_PROFILES。
所有返回使用 public DTO（脱敏，不暴露 secret）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.adapters.secrets import create_secret_store
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.service_definition import ServiceDefinition
from webapp.error_contract import domain_error_response


def mountain_service_router(data_dir: Path) -> APIRouter:
    router = APIRouter()
    secret_store, _ = create_secret_store(data_dir, encrypted=False)
    registry = FilesystemServiceRegistry(data_dir, secret_store)

    def _to_public(service: ServiceDefinition) -> dict[str, Any]:
        return registry.to_public_dict(service)

    @router.get("/api/v1/services")
    def list_services(
        capability: str | None = None,
        enabled: bool | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ):
        page = registry.list_services(capability=capability, enabled=enabled, limit=limit, cursor=cursor)
        next_cursor = page[-1].service_id if len(page) >= limit else None
        return {"items": [_to_public(s) for s in page], "total": len(page), "next_cursor": next_cursor}

    @router.post("/api/v1/services")
    def create_service(payload: dict[str, Any] = Body(...)):
        try:
            service = ServiceDefinition.from_dict(payload)
            created = registry.create_service(service)
            return _to_public(created)
        except DomainError as exc:
            return domain_error_response(exc, status_code=400)

    @router.get("/api/v1/services/{service_id}")
    def get_service(service_id: str):
        try:
            return _to_public(registry.get_service(service_id))
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.patch("/api/v1/services/{service_id}")
    def update_service(service_id: str, payload: dict[str, Any] = Body(...)):
        try:
            updated = registry.update_service(service_id, payload)
            return _to_public(updated)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)
        except DomainError as exc:
            status = 409 if exc.code == "REVISION_CONFLICT" else 400
            return domain_error_response(exc, status_code=status)

    @router.delete("/api/v1/services/{service_id}")
    def delete_service(service_id: str):
        try:
            registry.delete_service(service_id)
            return {"ok": True}
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)
        except DomainError as exc:
            return domain_error_response(exc, status_code=400)

    @router.post("/api/v1/services/{service_id}/activate")
    def activate_service(service_id: str):
        try:
            return _to_public(registry.activate_service(service_id))
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/services/{service_id}/deactivate")
    def deactivate_service(service_id: str):
        try:
            return _to_public(registry.deactivate_service(service_id))
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/services/{service_id}/probe")
    def probe_service(service_id: str):
        try:
            return registry.probe_service(service_id)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/services/{service_id}/default")
    def set_default(service_id: str):
        try:
            return _to_public(registry.set_default(service_id))
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)
        except DomainError as exc:
            return domain_error_response(exc, status_code=400)

    @router.get("/api/v1/services/{service_id}/secrets")
    def list_secrets(service_id: str):
        try:
            return {"secrets": registry.list_secrets(service_id)}
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/services/{service_id}/secrets")
    def set_secret(service_id: str, payload: dict[str, Any] = Body(...)):
        try:
            key = payload.get("key")
            value = payload.get("value")
            if not key or not value:
                return domain_error_response(
                    DomainError("VALIDATION_ERROR", "key 和 value 不能为空"), status_code=400
                )
            registry.set_secret(service_id, key, value)
            return {"secret_key": key, "configured": True}
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)
        except DomainError as exc:
            return domain_error_response(exc, status_code=400)

    @router.delete("/api/v1/services/{service_id}/secrets/{secret_key}")
    def delete_secret(service_id: str, secret_key: str):
        try:
            registry.delete_secret(service_id, secret_key)
            return {"ok": True}
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    return router
