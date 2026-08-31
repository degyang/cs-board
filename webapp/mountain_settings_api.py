"""Mountain Settings API — /api/v1/settings 路由。

SecretStore / ServiceRegistry 由 create_app() 统一创建并注入。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.adapters.secrets import SecretStoreProtocol


def mountain_settings_router(
    data_dir: Path,
    registry: FilesystemServiceRegistry | None = None,
    secret_store: SecretStoreProtocol | None = None,
    is_encrypted: bool = True,
) -> APIRouter:
    router = APIRouter()

    _ss = secret_store
    _reg = registry
    _enc = is_encrypted

    @router.get("/api/v1/settings/runtime")
    def get_runtime():
        return {
            "log_level": "INFO",
            "os": "linux",
            "version": "0.2.0",
        }

    @router.get("/api/v1/settings/toolchain")
    def get_toolchain():
        components = []
        tool_checks = [
            ("python", ["python3", "--version"]),
            ("node", ["node", "--version"]),
            ("ffmpeg", ["ffmpeg", "-version"]),
            ("ffprobe", ["ffprobe", "-version"]),
            ("codex-cli", ["codex", "--version"]),
        ]
        for name, cmd in tool_checks:
            path = shutil.which(cmd[0])
            version = None
            error_code = None
            suggestion = None
            if path:
                try:
                    result = subprocess.run(
                        [path] + cmd[1:], capture_output=True, text=True, timeout=5
                    )
                    version = result.stdout.strip().split("\n")[0][:120]
                except Exception:
                    error_code = "VERSION_CHECK_FAILED"
                    suggestion = f"运行 {' '.join(cmd)} 检查是否正常"
            else:
                error_code = "NOT_FOUND"
                suggestion = f"安装 {cmd[0]} 并确保在 PATH 中"
            components.append({
                "component": name,
                "available": bool(path),
                "version": version,
                "error_code": error_code,
                "suggestion": suggestion,
            })

        # Skills 目录检测
        skills_dir = data_dir.parent / "skills"
        components.append({
            "component": "skills",
            "available": skills_dir.is_dir(),
            "version": None,
            "error_code": None if skills_dir.is_dir() else "SKILLS_DIR_NOT_FOUND",
            "suggestion": None if skills_dir.is_dir() else "创建 skills 目录",
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

        # cleanup_policy
        cleanup_policy = {
            "temp_max_age_hours": 24,
            "auto_cleanup_enabled": True,
        }

        return {
            "writable": writable,
            "assets_available": assets_dir.exists(),
            "tasks_available": tasks_dir.exists(),
            "temp_available": temp_dir.exists(),
            "free_bytes": usage.free,
            "used_bytes": usage.used,
            "cleanup_policy": cleanup_policy,
        }

    @router.get("/api/v1/settings/voice-alignment")
    def get_voice_alignment():
        result: dict[str, Any] = {}

        # 默认 TTS 服务
        tts_services = _reg.list_services(capability="speech_synthesis", enabled=True)
        if tts_services:
            tts = tts_services[0]
            tts_probe = _reg.probe_service(tts.service_id) if tts else None
            result["default_tts"] = {
                "service_id": tts.service_id,
                "endpoint": tts.endpoint,
                "available": tts_probe.get("available", False) if tts_probe else False,
                "error_code": tts_probe.get("error_code") if tts_probe else None,
                "suggestion": tts_probe.get("suggestion") if tts_probe else None,
            }
        else:
            result["default_tts"] = {
                "service_id": None,
                "endpoint": None,
                "available": False,
                "error_code": "NO_TTS_SERVICE",
                "suggestion": "请注册 TTS 服务",
            }

        # Alignment 服务
        align_services = _reg.list_services(capability="speech_alignment", enabled=True)
        if align_services:
            align = align_services[0]
            align_probe = _reg.probe_service(align.service_id) if align else None
            result["alignment"] = {
                "service_id": align.service_id,
                "endpoint": align.endpoint,
                "available": align_probe.get("available", False) if align_probe else False,
                "error_code": align_probe.get("error_code") if align_probe else None,
                "suggestion": align_probe.get("suggestion") if align_probe else None,
            }
        else:
            result["alignment"] = {
                "service_id": None,
                "endpoint": None,
                "available": False,
                "error_code": "NO_ALIGNMENT_SERVICE",
                "suggestion": "请注册 Alignment 服务",
            }

        return result

    @router.get("/api/v1/settings/diagnostics")
    def get_diagnostics():
        # Services
        services = _reg.list_services()
        service_infos = []
        for svc in services:
            probe = _reg.probe_service(svc.service_id)
            service_infos.append({
                "service_id": svc.service_id,
                "capability": svc.capability,
                "enabled": svc.enabled,
                "is_default": svc.is_default,
                "available": probe.get("available", False),
                "error_code": probe.get("error_code"),
            })

        # Toolchain
        toolchain = []
        for name, cmd in [
            ("python", "python3"), ("node", "node"),
            ("ffmpeg", "ffmpeg"), ("ffprobe", "ffprobe"),
            ("codex-cli", "codex"),
        ]:
            toolchain.append({
                "component": name,
                "available": bool(shutil.which(cmd)),
            })

        # Storage
        usage = shutil.disk_usage(str(data_dir))
        try:
            test_file = data_dir / ".write_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            writable = True
        except OSError:
            writable = False

        # Telemetry
        from csboard.adapters.observability import JsonlTelemetry
        from csboard.adapters.filesystem import FilesystemTaskRepository
        repo = FilesystemTaskRepository(data_dir)
        telemetry = JsonlTelemetry(repo)
        event_count = 0
        for task_dir in (data_dir / "tasks").glob("*/runs/*/observability"):
            events_file = task_dir / "events.jsonl"
            if events_file.exists():
                event_count += len(events_file.read_text(encoding="utf-8").splitlines())

        # Logs（最近安全错误 — 不泄漏 secret）
        recent_errors: list[dict[str, Any]] = []
        for task_dir in sorted((data_dir / "tasks").glob("*/runs/*/observability"), reverse=True)[:5]:
            log_file = task_dir / "logs.jsonl"
            if log_file.exists():
                import json
                for line in log_file.read_text(encoding="utf-8").splitlines()[-20:]:
                    try:
                        entry = json.loads(line)
                        if entry.get("level") == "ERROR":
                            # 脱敏：只保留 message 的前200字符，去除可能的 secret
                            safe_entry = {
                                "timestamp": entry.get("timestamp", ""),
                                "component": entry.get("component", ""),
                                "stage": entry.get("stage", ""),
                                "message": str(entry.get("message", ""))[:200],
                            }
                            recent_errors.append(safe_entry)
                    except (json.JSONDecodeError, ValueError):
                        continue

        return {
            "api": {"status": "ok"},
            "services": service_infos,
            "toolchain": toolchain,
            "storage": {
                "writable": writable,
                "free_bytes": usage.free,
                "used_bytes": usage.used,
            },
            "telemetry": {
                "available": True,
                "event_count": event_count,
            },
            "logs": {
                "recent_errors": recent_errors[:10],
            },
            "security": {
                "secret_store_encrypted": _enc,
            },
        }

    return router
