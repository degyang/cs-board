"""Mountain Service API — /api/v1/services 端点。

动态服务注册。
不依赖 PROVIDER_PROFILES。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.adapters.secrets import create_secret_store, mask_secret
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.service_definition import ServiceDefinition


def _error_response(status_code: int, code: str, message: str, retryable: bool = False) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "retryable": retryable}},
    )


def mountain_service_router(data_dir: Path) -> APIRouter:
    """创建 /api/v1/services 路由器。"""
    secret_store, _ = create_secret_store(data_dir, encrypted=False)
    registry = FilesystemServiceRegistry(data_dir, secret_store)
    router = APIRouter(prefix="/api/v1/services", tags=["mountain-services"])

    @router.get("")
    def list_services(
        capability: str | None = None,
        enabled: bool | None = None,
        q: str | None = None,
        cursor: str | None = None,
        limit: int = Query(50, ge=1, le=200),
    ) -> dict[str, Any]:
        services = registry.list_services(capability=capability, enabled=enabled)
        if q:
            services = [s for s in services if q.lower() in s.display_name.lower() or q.lower() in s.service_id.lower()]
        # cursor 分页
        if cursor:
            ids = [s.service_id for s in services]
            if cursor in ids:
                idx = ids.index(cursor)
                services = services[idx + 1:]
        page = services[:limit]
        next_cursor = services[limit].service_id if len(services) > limit else None
        return {
            "items": [s.to_dict() for s in page],
            "next_cursor": next_cursor,
            "total": len(services),
        }

    @router.post("")
    def create_service(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
        try:
            service = ServiceDefinition.from_dict(body)
            created = registry.create_service(service)
            return created.to_dict()
        except DomainError as exc:
            return _error_response(422, exc.code, exc.message)

    @router.get("/{service_id}")
    def get_service(service_id: str) -> dict[str, Any]:
        try:
            return registry.get_service(service_id).to_dict()
        except NotFoundError as exc:
            return _error_response(404, "NOT_FOUND", str(exc))

    @router.patch("/{service_id}")
    def update_service(service_id: str, body: dict[str, Any] = Body(...)) -> dict[str, Any]:
        try:
            updated = registry.update_service(service_id, body)
            return updated.to_dict()
        except NotFoundError as exc:
            return _error_response(404, "NOT_FOUND", str(exc))
        except DomainError as exc:
            return _error_response(422, exc.code, exc.message)

    @router.delete("/{service_id}")
    def delete_service(service_id: str) -> dict[str, Any]:
        try:
            registry.delete_service(service_id)
            return {"ok": True}
        except NotFoundError as exc:
            return _error_response(404, "NOT_FOUND", str(exc))
        except DomainError as exc:
            return _error_response(409, exc.code, exc.message)

    @router.post("/{service_id}/activate")
    def activate_service(service_id: str) -> dict[str, Any]:
        try:
            return registry.activate_service(service_id).to_dict()
        except NotFoundError as exc:
            return _error_response(404, "NOT_FOUND", str(exc))

    @router.post("/{service_id}/deactivate")
    def deactivate_service(service_id: str) -> dict[str, Any]:
        try:
            return registry.deactivate_service(service_id).to_dict()
        except NotFoundError as exc:
            return _error_response(404, "NOT_FOUND", str(exc))

    @router.post("/{service_id}/probe")
    def probe_service(service_id: str) -> dict[str, Any]:
        try:
            return registry.probe_service(service_id)
        except NotFoundError as exc:
            return _error_response(404, "NOT_FOUND", str(exc))

    @router.post("/{service_id}/default")
    def set_default(service_id: str) -> dict[str, Any]:
        try:
            return registry.set_default(service_id).to_dict()
        except NotFoundError as exc:
            return _error_response(404, "NOT_FOUND", str(exc))

    @router.get("/{service_id}/secrets")
    def list_secrets(service_id: str) -> dict[str, Any]:
        try:
            secrets = registry.list_secrets(service_id)
            return {"items": secrets, "total": len(secrets)}
        except NotFoundError as exc:
            return _error_response(404, "NOT_FOUND", str(exc))

    @router.post("/{service_id}/secrets")
    def set_secret(service_id: str, body: dict[str, Any] = Body(...)) -> dict[str, Any]:
        key = body.get("key", "")
        value = body.get("value", "")
        if not key or not value:
            return _error_response(422, "VALIDATION_ERROR", "key 和 value 不能为空")
        try:
            registry.set_secret(service_id, key, value)
            return {
                "secret_key": key,
                "configured": True,
                "masked_value": mask_secret(value),
                "updated_at": "",
            }
        except NotFoundError as exc:
            return _error_response(404, "NOT_FOUND", str(exc))
        except DomainError as exc:
            return _error_response(422, exc.code, exc.message)

    @router.delete("/{service_id}/secrets/{secret_key}")
    def delete_secret(service_id: str, secret_key: str) -> dict[str, Any]:
        try:
            registry.delete_secret(service_id, secret_key)
            return {"ok": True}
        except NotFoundError as exc:
            return _error_response(404, "NOT_FOUND", str(exc))

    return router
