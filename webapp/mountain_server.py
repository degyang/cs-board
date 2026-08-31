"""Mountain Server — FastAPI 应用工厂。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from webapp.mountain_asset_api import mountain_asset_router
from webapp.mountain_service_api import mountain_service_router
from webapp.mountain_settings_api import mountain_settings_router

_DATA_DIR = Path(os.environ.get("CSBOARD_DATA_DIR", ".webapp"))


def create_app(data_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Mountain Server", version="0.1.0")

    effective_data_dir = data_dir or _DATA_DIR
    app.state.data_dir = effective_data_dir

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

    # API routers
    app.include_router(mountain_asset_router(effective_data_dir))
    app.include_router(mountain_service_router(effective_data_dir))
    app.include_router(mountain_settings_router(effective_data_dir))

    # Health endpoint
    @app.get("/api/v1/health")
    def health():
        return {"status": "ok"}

    # SPA fallback: serve web-v2/dist for non-/api/ routes
    web_dist = Path(__file__).resolve().parents[1] / "web-v2" / "dist"

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        if path.startswith("api/"):
            return JSONResponse({"error": {"code": "NOT_FOUND", "message": f"API 路径不存在: /{path}", "retryable": False}}, status_code=404)

        if web_dist.exists():
            file_path = web_dist / path
            if file_path.is_file():
                return FileResponse(file_path)
            index = web_dist / "index.html"
            if index.is_file():
                return FileResponse(index)

        return JSONResponse({"error": {"code": "NOT_FOUND", "message": "web-v2 未构建或路径不存在", "retryable": False}}, status_code=404)

    return app


app = create_app()
