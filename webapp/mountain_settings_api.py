"""Mountain Settings API — /api/v1/settings 端点。

服务配置、运行环境状态、诊断入口。
不依赖 legacy 模块。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from csboard.adapters.dynamic_service_registry import DynamicServiceRegistry
from csboard.adapters.provider_factory import ProviderFactory
from csboard.adapters.secrets import mask_secret
from csboard.domain.errors import DomainError, NotFoundError


def mountain_settings_router(data_dir: Path) -> APIRouter:
    """创建 /api/v1/settings 路由器。"""
    provider_factory = ProviderFactory(data_dir)
    registry = DynamicServiceRegistry(provider_factory)
    router = APIRouter(prefix="/api/v1/settings", tags=["mountain-settings"])

    # ── Providers ──────────────────────────────────────────────────

    @router.get("/providers")
    def list_providers() -> dict[str, Any]:
        """列出所有 Provider 配置状态。"""
        services = registry.list_services()
        return {
            "items": services,
            "total": len(services),
        }

    @router.get("/providers/{provider_id}")
    def get_provider(provider_id: str) -> dict[str, Any]:
        """获取 Provider 详情。"""
        try:
            return registry.get_service(provider_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @router.patch("/providers/{provider_id}")
    def update_provider(
        provider_id: str,
        config: dict[str, Any] = Body(...),
    ) -> dict[str, Any]:
        """更新 Provider 配置（白名单字段）。"""
        try:
            registry.update_service_config(provider_id, config)
            return registry.get_service(provider_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except DomainError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @router.post("/providers/{provider_id}/secrets")
    def set_provider_secret(
        provider_id: str,
        body: dict[str, Any] = Body(...),
    ) -> dict[str, Any]:
        """设置 Provider Secret。不回显明文。"""
        secret_key = body.get("key", "")
        secret_value = body.get("value", "")
        if not secret_key or not secret_value:
            raise HTTPException(status_code=422, detail="key 和 value 不能为空")
        try:
            registry.set_service_secret(provider_id, secret_key, secret_value)
            return {
                "ok": True,
                "service_id": provider_id,
                "secret_key": secret_key,
                "has_secret": True,
                "masked_value": mask_secret(secret_value),
            }
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except DomainError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    # ── Runtime ────────────────────────────────────────────────────

    @router.get("/runtime")
    def get_runtime() -> dict[str, Any]:
        """获取运行环境状态。"""
        return registry.get_runtime_status()

    @router.get("/runtime/voice-alignment")
    def get_voice_alignment() -> dict[str, Any]:
        """获取语音对齐状态。"""
        return registry.get_voice_alignment_status()

    # ── Diagnostics ────────────────────────────────────────────────

    @router.get("/diagnostics")
    def get_diagnostics() -> dict[str, Any]:
        """诊断入口。"""
        runtime = registry.get_runtime_status()
        health = registry.check_all_health()
        return {
            "runtime": runtime,
            "health": health,
        }

    return router
