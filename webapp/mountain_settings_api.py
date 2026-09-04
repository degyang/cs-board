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
                "path": path,
                "error_code": error_code,
                "suggestion": suggestion,
            })

        # Skills 目录检测
        # Skills are project capabilities, not runtime data.  A caller may
        # place CSBOARD_DATA_DIR anywhere (the manual integration flow uses
        # /tmp), so deriving this path from data_dir makes an installed skill
        # disappear as soon as storage is relocated.
        skills_dir = Path(__file__).resolve().parents[1] / "skills"
        components.append({
            "component": "skills",
            "available": skills_dir.is_dir(),
            "version": None,
            "error_code": None if skills_dir.is_dir() else "SKILLS_DIR_NOT_FOUND",
            "suggestion": None if skills_dir.is_dir() else "创建 skills 目录",
        })

        return {"tools": components}

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
            "cleanup_policy": "temp_max_age_hours=24",
            "error_code": None,
            "suggestion": None,
        }

    def _service_to_alignment_summary(svc) -> dict[str, Any]:
        """将 ServiceDefinition 转为 VoiceAlignmentServiceSummary DTO。"""
        probe = _reg.get_cached_probe(svc.service_id)
        if probe is None:
            probe = _reg.probe_service(svc.service_id)
        return {
            "service_id": svc.service_id,
            "display_name": svc.display_name or svc.service_id,
            "capability": svc.capability,
            "adapter_type": svc.adapter_type or "",
            "endpoint": svc.endpoint,
            "model": svc.model or None,
            "timeout": svc.config.get("timeout"),
            "availability": {
                "available": probe.get("available", False),
                "checked_at": probe.get("checked_at"),
                "latency_ms": probe.get("latency_ms"),
                "component": probe.get("component"),
                "error_code": probe.get("error_code"),
                "suggestion": probe.get("suggestion"),
            },
        }

    def _service_to_probe_summary(svc) -> dict[str, Any]:
        """将 ServiceDefinition 转为 ProbeSummary DTO。"""
        probe = _reg.get_cached_probe(svc.service_id)
        if probe is None:
            probe = _reg.probe_service(svc.service_id)
        return {
            "available": probe.get("available", False),
            "checked_at": probe.get("checked_at"),
            "latency_ms": probe.get("latency_ms"),
            "component": probe.get("component"),
            "error_code": probe.get("error_code"),
            "suggestion": probe.get("suggestion"),
        }

    @router.get("/api/v1/settings/voice-alignment")
    def get_voice_alignment():
        # speech_synthesis
        tts_services = _reg.list_services(capability="speech_synthesis", enabled=True)
        speech_synthesis = _service_to_alignment_summary(tts_services[0]) if tts_services else None

        # speech_alignment
        align_services = _reg.list_services(capability="speech_alignment", enabled=True)
        speech_alignment = _service_to_alignment_summary(align_services[0]) if align_services else None

        # indextts
        indextts_services = _reg.list_services(capability="indextts", enabled=True)
        indextts = _service_to_probe_summary(indextts_services[0]) if indextts_services else None

        # whisper
        whisper_services = _reg.list_services(capability="whisper", enabled=True)
        whisper = _service_to_probe_summary(whisper_services[0]) if whisper_services else None

        return {
            "speech_synthesis": speech_synthesis,
            "speech_alignment": speech_alignment,
            "indextts": indextts,
            "whisper": whisper,
        }

    @router.get("/api/v1/settings/diagnostics")
    def get_diagnostics():
        # Services — aggregated summary (DiagnosticsServiceSummary)
        services = _reg.list_services()
        available_count = 0
        for svc in services:
            probe = _reg.get_cached_probe(svc.service_id)
            if probe is None:
                probe = _reg.probe_service(svc.service_id)
            if probe.get("available", False):
                available_count += 1
        service_summary = {
            "total": len(services),
            "available": available_count,
            "unavailable": len(services) - available_count,
        }

        # Toolchain — aggregated summary (DiagnosticsToolchainSummary)
        tool_names = ["python", "node", "ffmpeg", "ffprobe", "codex-cli"]
        tool_available = sum(1 for name in tool_names if shutil.which(
            "python3" if name == "python" else name
        ))
        toolchain_summary = {
            "total": len(tool_names),
            "available": tool_available,
            "missing": len(tool_names) - tool_available,
        }

        # Storage (DiagnosticsStorageSummary)
        usage = shutil.disk_usage(str(data_dir))
        try:
            test_file = data_dir / ".write_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            writable = True
        except OSError:
            writable = False

        # Telemetry (DiagnosticsTelemetry)
        from csboard.adapters.observability import JsonlTelemetry
        from csboard.adapters.filesystem import FilesystemTaskRepository
        from csboard.adapters.observability.redactor import DefaultRedactor
        repo = FilesystemTaskRepository(data_dir)
        telemetry = JsonlTelemetry(repo)
        redactor = DefaultRedactor()

        # Logs — redacted recent errors (DiagnosticsLogs)
        recent_error_count = 0
        log_path = None
        recent_errors: list[dict[str, Any]] = []
        import json as _json
        for task_dir in sorted((data_dir / "tasks").glob("*/runs/*/observability"), reverse=True)[:5]:
            log_file = task_dir / "logs.jsonl"
            if log_file.exists():
                if log_path is None:
                    log_path = str(log_file)
                for line in log_file.read_text(encoding="utf-8").splitlines()[-20:]:
                    try:
                        entry = _json.loads(line)
                        if entry.get("level") == "ERROR":
                            recent_error_count += 1
                            # 使用 DefaultRedactor 结构化脱敏
                            safe_entry = redactor.redact({
                                "timestamp": entry.get("timestamp", ""),
                                "component": entry.get("component", ""),
                                "stage": entry.get("stage", ""),
                                "message": entry.get("message", ""),
                                "details": entry.get("details", {}),
                            })
                            recent_errors.append(safe_entry)
                    except (_json.JSONDecodeError, ValueError):
                        continue

        return {
            "api": {
                "status": "healthy",
                "endpoint": None,
                "latency_ms": None,
            },
            "services": service_summary,
            "toolchain": toolchain_summary,
            "storage": {
                "writable": writable,
                "free_bytes": usage.free,
                "used_bytes": usage.used,
            },
            "telemetry": {
                "enabled": True,
                "endpoint": None,
            },
            "logs": {
                "recent_errors": recent_error_count,
                "log_path": log_path,
            },
            "recent_errors": recent_errors[:10],
        }

    return router
