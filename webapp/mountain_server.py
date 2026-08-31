"""Mountain Server — 唯一组合根。

mountain_server.create_app() 是唯一组合根。只在这里创建一次：
- SecretStore
- FilesystemServiceRegistry
- ServiceResolver
- ProviderFactory
- MountainCommands / Application service

随后注入 Task、Service、Settings Router。Router 不得再次调用 create_secret_store()。

不导入 webapp.server、LegacyJobBridge、JOBS。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from webapp.error_contract import domain_error_response

# 稳定默认目录：使用 $HOME/.csboard 而非相对路径
_DEFAULT_DATA_DIR = Path(os.environ.get("CSBOARD_DATA_DIR", Path.home() / ".csboard"))


def create_app(data_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Mountain Server", version="0.2.0")

    effective_data_dir = data_dir or _DEFAULT_DATA_DIR
    effective_data_dir.mkdir(parents=True, exist_ok=True)
    app.state.data_dir = effective_data_dir

    # 确保所需子目录存在
    for subdir in ("tasks", "assets", "temp", "settings"):
        (effective_data_dir / subdir).mkdir(parents=True, exist_ok=True)

    # CORS
    origins = [
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:13000",
        "http://127.0.0.1:13000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 唯一组合根：创建所有共享组件 ──────────────────────────
    from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
    from csboard.adapters.secrets import create_secret_store
    from csboard.application.service_resolver import ServiceResolver
    from csboard.adapters.provider_factory import ProviderFactory

    # 检查是否允许明文 secret
    allow_plaintext = os.environ.get("CSBOARD_ALLOW_PLAINTEXT_SECRETS", "") == "1"

    # 默认要求加密并 fail closed
    try:
        secret_store, is_encrypted = create_secret_store(
            effective_data_dir, encrypted=not allow_plaintext
        )
    except Exception:
        if allow_plaintext:
            from csboard.adapters.secrets.secret_store import PlaintextSecretStore
            secret_store = PlaintextSecretStore(effective_data_dir / ".secrets")
            is_encrypted = False
        else:
            raise

    # 共享组件：所有 Router 使用同一实例
    service_registry = FilesystemServiceRegistry(effective_data_dir, secret_store)
    service_resolver = ServiceResolver(service_registry)
    provider_factory = ProviderFactory(
        effective_data_dir,
        secret_store=secret_store,
        is_encrypted=is_encrypted,
    )

    # 挂载路由 — 注入共享组件
    from webapp.mountain_task_api import mountain_task_router
    from webapp.mountain_asset_api import mountain_asset_router
    from webapp.mountain_service_api import mountain_service_router
    from webapp.mountain_settings_api import mountain_settings_router

    task_router = mountain_task_router(effective_data_dir)
    # 注入 ServiceResolver 和 ProviderFactory 到 task router
    if hasattr(task_router, 'state_set_dependencies'):
        task_router.state_set_dependencies(service_resolver, provider_factory)

    app.include_router(task_router)
    app.include_router(mountain_asset_router(effective_data_dir))
    app.include_router(mountain_service_router(
        effective_data_dir, registry=service_registry, secret_store=secret_store,
    ))
    app.include_router(mountain_settings_router(
        effective_data_dir, registry=service_registry, secret_store=secret_store,
        is_encrypted=is_encrypted,
    ))

    # Health endpoint — 真实健康检查
    @app.get("/api/v1/health")
    def health():
        checks: dict[str, Any] = {}
        overall = "ok"

        # TaskRepository
        try:
            from csboard.adapters.filesystem import FilesystemTaskRepository
            _repo = FilesystemTaskRepository(effective_data_dir)
            checks["task_repository"] = {"status": "ok"}
        except Exception:
            checks["task_repository"] = {"status": "failed", "error_code": "INIT_FAILED"}
            overall = "failed"

        # AssetRepository
        try:
            from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
            _asset_repo = FilesystemAssetRepository(effective_data_dir)
            checks["asset_repository"] = {"status": "ok"}
        except Exception:
            checks["asset_repository"] = {"status": "failed", "error_code": "INIT_FAILED"}
            overall = "degraded"

        # ServiceRegistry
        try:
            service_count = len(service_registry.list_services())
            checks["service_registry"] = {"status": "ok", "service_count": service_count}
        except Exception:
            checks["service_registry"] = {"status": "failed", "error_code": "INIT_FAILED"}
            overall = "degraded"

        # SecretStore
        checks["secret_store"] = {
            "status": "ok",
            "encrypted": is_encrypted,
        }
        if not is_encrypted:
            checks["secret_store"]["warning"] = "SECRET_STORE_PLAINTEXT"

        # Storage writable
        try:
            test_file = effective_data_dir / ".health_check"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            checks["storage"] = {"status": "ok", "writable": True}
        except OSError:
            checks["storage"] = {"status": "failed", "writable": False}
            overall = "failed"

        return {"status": overall, "checks": checks}

    # SPA fallback
    web_dist = Path(__file__).resolve().parents[1] / "web-v2" / "dist"

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        if path.startswith("api/"):
            return JSONResponse(
                {"error": {"code": "NOT_FOUND", "message": f"API 路径不存在: /{path}", "retryable": False}},
                status_code=404,
            )

        if web_dist.exists():
            file_path = web_dist / path
            if file_path.is_file():
                return FileResponse(file_path)
            index = web_dist / "index.html"
            if index.is_file():
                return FileResponse(index)

        return JSONResponse(
            {"error": {"code": "NOT_FOUND", "message": "web-v2 未构建或路径不存在", "retryable": False}},
            status_code=404,
        )

    return app


app = create_app()
