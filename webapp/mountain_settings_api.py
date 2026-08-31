"""Mountain Settings API — /api/v1/settings 路由。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.adapters.secrets import create_secret_store


def mountain_settings_router(data_dir: Path) -> APIRouter:
    router = APIRouter()
    secret_store, _ = create_secret_store(data_dir, encrypted=False)
    registry = FilesystemServiceRegistry(data_dir, secret_store)

    @router.get("/api/v1/settings/runtime")
    def get_runtime():
        return {
            "log_level": "INFO",
            "os": "linux",
            "version": "0.1.0",
        }

    @router.get("/api/v1/settings/toolchain")
    def get_toolchain():
        components = []
        for name, cmd in [
            ("python", "python3"),
            ("node", "node"),
            ("ffmpeg", "ffmpeg"),
            ("ffprobe", "ffprobe"),
        ]:
            path = shutil.which(cmd)
            version = None
            error_code = None
            suggestion = None
            if path:
                try:
                    result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
                    version = result.stdout.strip().split("\n")[0]
                except Exception as exc:
                    error_code = "VERSION_CHECK_FAILED"
                    suggestion = f"运行 {cmd} --version 检查是否正常"
            else:
                error_code = "NOT_FOUND"
                suggestion = f"安装 {cmd} 并确保在 PATH 中"
            components.append({
                "component": name,
                "available": bool(path),
                "version": version,
                "error_code": error_code,
                "suggestion": suggestion,
            })
        return {"items": components}

    @router.get("/api/v1/settings/storage")
    def get_storage():
        assets_dir = data_dir / "assets"
        tasks_dir = data_dir / "tasks"
        temp_dir = data_dir / "temp"

        try:
            test_file = data_dir / ".write_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            writable = True
        except OSError:
            writable = False

        usage = shutil.disk_usage(str(data_dir))
        return {
            "writable": writable,
            "assets_available": assets_dir.exists(),
            "tasks_available": tasks_dir.exists(),
            "temp_available": temp_dir.exists(),
            "free_bytes": usage.free,
            "used_bytes": usage.used,
        }

    @router.get("/api/v1/settings/voice-alignment")
    def get_voice_alignment():
        services = registry.list_services(capability="speech_alignment")
        if not services:
            return {
                "service_id": None,
                "endpoint": None,
                "available": False,
            }
        svc = services[0]
        return {
            "service_id": svc.service_id,
            "endpoint": svc.endpoint,
            "available": svc.enabled,
        }

    @router.get("/api/v1/settings/diagnostics")
    def get_diagnostics():
        from csboard.adapters.observability import JsonlTelemetry
        from datetime import datetime, timezone

        services = registry.list_services()
        service_infos = []
        for svc in services:
            service_infos.append({
                "service_id": svc.service_id,
                "capability": svc.capability,
                "enabled": svc.enabled,
                "is_default": svc.is_default,
            })

        toolchain = []
        for name, cmd in [("python", "python3"), ("node", "node"), ("ffmpeg", "ffmpeg"), ("ffprobe", "ffprobe")]:
            toolchain.append({
                "component": name,
                "available": bool(shutil.which(cmd)),
            })

        usage = shutil.disk_usage(str(data_dir))
        try:
            test_file = data_dir / ".write_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            writable = True
        except OSError:
            writable = False

        return {
            "services": service_infos,
            "toolchain": toolchain,
            "storage": {
                "writable": writable,
                "free_bytes": usage.free,
                "used_bytes": usage.used,
            },
            "telemetry": {
                "available": True,
                "event_count": 0,
            },
        }

    return router
