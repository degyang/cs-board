"""Mountain 纯净入口 — 仅挂载 /api/v1 路由。

不依赖 webapp.server、LegacyJobBridge、JOBS 或任何 legacy 模块。
CORS 使用明确白名单，不使用 allow_origins=["*"] + credentials。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from webapp.mountain_asset_api import mountain_asset_router
from webapp.mountain_settings_api import mountain_settings_router
from webapp.mountain_v1_api import mountain_v1_router


def create_app(data_dir: Path) -> FastAPI:
    """创建 Mountain 应用。"""
    app = FastAPI(title="Mountain", version="2.0.0")

    # 挂载路由
    app.include_router(mountain_v1_router(data_dir))
    app.include_router(mountain_asset_router(data_dir))
    app.include_router(mountain_settings_router(data_dir))

    # CORS 明确白名单
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:13000", "http://127.0.0.1:13000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app
