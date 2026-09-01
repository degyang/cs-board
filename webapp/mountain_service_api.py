"""Mountain Service API — /api/v1/services 路由。

动态 Service API，不依赖 PROVIDER_PROFILES。
所有返回使用 public DTO（脱敏，不暴露 secret）。
SecretStore / ServiceRegistry 由 create_app() 统一创建并注入。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.adapters.secrets import SecretStoreProtocol
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.service_definition import ServiceDefinition
from webapp.error_contract import domain_error_response


def mountain_service_router(
    data_dir: Path,
    registry: FilesystemServiceRegistry | None = None,
    secret_store: SecretStoreProtocol | None = None,
) -> APIRouter:
    router = APIRouter()

    _ss = secret_store
    _reg = registry

    def _to_full_view(service: ServiceDefinition) -> dict[str, Any]:
        """返回完整 ServiceDefinition View，包含 config_status / availability / secret_status。"""
        base = _reg.to_public_dict(service)

        # config_status
        if service.adapter_type == "openai_compatible":
            required_fields = {"endpoint", "model"}
        elif service.adapter_type == "indextts":
            required_fields = {"endpoint"}
        else:
            required_fields = set()
        configured_fields = set()
        missing_fields = []
        for f in required_fields:
            val = getattr(service, f, "") or service.config.get(f, "")
            if val:
                configured_fields.add(f)
            else:
                missing_fields.append(f)
        missing_secrets = []
        configured_secrets = []
        for sk in service.required_secrets:
            full_key = f"{service.service_id}_{sk}"
            if _ss.get(full_key):
                configured_secrets.append(sk)
            else:
                missing_secrets.append(sk)
        base["config_status"] = {
            "configured": len(missing_fields) == 0 and len(missing_secrets) == 0,
            "missing_fields": missing_fields,
            "missing_secrets": missing_secrets,
        }

        # availability（使用缓存的 probe 结果，不做实时探测）
        cached_probe = _reg.get_cached_probe(service.service_id)
        if cached_probe:
            base["availability"] = {
                "available": cached_probe.get("available", False),
                "checked_at": cached_probe.get("checked_at", ""),
                "latency_ms": cached_probe.get("latency_ms", 0),
                "component": cached_probe.get("component", service.service_id),
                "error_code": cached_probe.get("error_code"),
                "suggestion": cached_probe.get("suggestion"),
            }
        else:
            base["availability"] = {
                "available": False,
                "checked_at": "",
                "latency_ms": 0,
                "component": service.service_id,
                "error_code": "NOT_PROBED",
                "suggestion": "尚未探测，请调用 /probe 端点",
            }

        # secret_status
        base["secret_status"] = {
            "configured": len(missing_secrets) == 0,
            "required": service.required_secrets,
            "missing": missing_secrets,
        }

        return base

    @router.get("/api/v1/services")
    def list_services(
        capability: str | None = None,
        enabled: bool | None = None,
        q: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ):
        # 获取全量后计算 filtered total
        all_filtered = _reg.list_services(capability=capability, enabled=enabled)
        if q:
            needle = q.casefold()
            all_filtered = [
                service for service in all_filtered
                if needle in service.display_name.casefold()
                or needle in service.service_id.casefold()
                or needle in service.model.casefold()
            ]
        total = len(all_filtered)
        # 分页
        if cursor:
            cursor_idx = -1
            for idx, s in enumerate(all_filtered):
                if s.service_id == cursor:
                    cursor_idx = idx + 1
                    break
            if cursor_idx > 0:
                all_filtered = all_filtered[cursor_idx:]
        effective_limit = max(1, min(limit, 100))
        page = all_filtered[:effective_limit]
        next_cursor = page[-1].service_id if len(page) >= effective_limit and len(all_filtered) > effective_limit else None
        return {"items": [_to_full_view(s) for s in page], "total": total, "next_cursor": next_cursor}

    @router.post("/api/v1/services")
    def create_service(payload: dict[str, Any] = Body(...)):
        try:
            service = ServiceDefinition.from_dict(payload)
            created = _reg.create_service(service)
            return _to_full_view(created)
        except DomainError as exc:
            return domain_error_response(exc, status_code=400)

    @router.get("/api/v1/services/{service_id}")
    def get_service(service_id: str):
        try:
            return _to_full_view(_reg.get_service(service_id))
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.patch("/api/v1/services/{service_id}")
    def update_service(service_id: str, payload: dict[str, Any] = Body(...)):
        try:
            updated = _reg.update_service(service_id, payload)
            return _to_full_view(updated)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)
        except DomainError as exc:
            status = 409 if exc.code == "REVISION_CONFLICT" else 400
            return domain_error_response(exc, status_code=status)

    @router.delete("/api/v1/services/{service_id}")
    def delete_service(service_id: str):
        try:
            _reg.delete_service(service_id)
            return {"ok": True}
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)
        except DomainError as exc:
            return domain_error_response(exc, status_code=400)

    @router.post("/api/v1/services/{service_id}/activate")
    def activate_service(service_id: str):
        try:
            return _to_full_view(_reg.activate_service(service_id))
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/services/{service_id}/deactivate")
    def deactivate_service(service_id: str):
        try:
            return _to_full_view(_reg.deactivate_service(service_id))
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/services/{service_id}/probe")
    def probe_service(service_id: str):
        try:
            return _reg.probe_service(service_id, force=True)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/services/{service_id}/default")
    def set_default(service_id: str):
        try:
            return _to_full_view(_reg.set_default(service_id))
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)
        except DomainError as exc:
            return domain_error_response(exc, status_code=400)

    @router.get("/api/v1/services/{service_id}/secrets")
    def list_secrets(service_id: str):
        try:
            items = _reg.list_secrets(service_id)
            return {"items": items, "total": len(items)}
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
            _reg.set_secret(service_id, key, value)
            return {"secret_key": key, "configured": True}
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)
        except DomainError as exc:
            return domain_error_response(exc, status_code=400)

    @router.delete("/api/v1/services/{service_id}/secrets/{secret_key}")
    def delete_secret(service_id: str, secret_key: str):
        try:
            _reg.delete_secret(service_id, secret_key)
            return {"ok": True}
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    return router
