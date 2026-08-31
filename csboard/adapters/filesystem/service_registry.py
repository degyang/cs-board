"""FilesystemServiceRegistry — 文件系统服务注册表实现。

数据位置：<data_dir>/settings/services/*.json
运行时不依赖 PROVIDER_PROFILES。
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from csboard.adapters.secrets import SecretStoreProtocol, mask_secret
from csboard.application.context import utc_now
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.service_definition import ServiceDefinition


class FilesystemServiceRegistry:
    """文件系统服务注册表。"""

    def __init__(self, data_dir: Path, secret_store: SecretStoreProtocol) -> None:
        self._data_dir = data_dir
        self._services_dir = data_dir / "settings" / "services"
        self._services_dir.mkdir(parents=True, exist_ok=True)
        self._secret_store = secret_store

    def _service_path(self, service_id: str) -> Path:
        return self._services_dir / f"{service_id}.json"

    def _load_service(self, service_id: str) -> ServiceDefinition:
        path = self._service_path(service_id)
        if not path.exists():
            raise NotFoundError(f"服务 '{service_id}' 不存在")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ServiceDefinition.from_dict(data)
        except (json.JSONDecodeError, OSError) as exc:
            raise NotFoundError(f"服务 '{service_id}' 数据损坏")

    def _save_service(self, service: ServiceDefinition) -> None:
        path = self._service_path(service.service_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(service.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _list_all(self) -> list[ServiceDefinition]:
        result = []
        for path in self._services_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                result.append(ServiceDefinition.from_dict(data))
            except (json.JSONDecodeError, OSError, KeyError):
                continue
        return result

    def list_services(self, capability: str | None = None, enabled: bool | None = None) -> list[ServiceDefinition]:
        """列出服务。"""
        all_services = self._list_all()
        filtered = []
        for s in all_services:
            if capability and s.capability != capability:
                continue
            if enabled is not None and s.enabled != enabled:
                continue
            filtered.append(s)
        # 排序：enabled first, is_default first, priority ASC, service_id ASC
        filtered.sort(key=lambda s: (not s.enabled, not s.is_default, s.priority, s.service_id))
        return filtered

    def get_service(self, service_id: str) -> ServiceDefinition:
        return self._load_service(service_id)

    def create_service(self, service: ServiceDefinition) -> ServiceDefinition:
        if not service.service_id:
            service.service_id = uuid.uuid4().hex[:16]
        if self._service_path(service.service_id).exists():
            raise DomainError("CONFLICT", f"服务 '{service.service_id}' 已存在")
        now = utc_now()
        service.created_at = now
        service.updated_at = now
        service.revision = 1
        self._save_service(service)
        return service

    def update_service(self, service_id: str, updates: dict[str, Any]) -> ServiceDefinition:
        service = self._load_service(service_id)
        # 禁止更新的字段
        protected = {"service_id", "schema_version", "created_at"}
        for key in updates:
            if key in protected:
                raise DomainError("VALIDATION_ERROR", f"不允许更新字段: {key}")
        for key, value in updates.items():
            if hasattr(service, key):
                setattr(service, key, value)
        service.revision += 1
        service.updated_at = utc_now()
        self._save_service(service)
        return service

    def delete_service(self, service_id: str) -> None:
        service = self._load_service(service_id)
        if service.is_default and service.enabled:
            raise DomainError("CONFLICT", "不能删除当前默认且启用的服务，请先停用或取消默认")
        path = self._service_path(service_id)
        path.unlink(missing_ok=True)

    def activate_service(self, service_id: str) -> ServiceDefinition:
        service = self._load_service(service_id)
        service.enabled = True
        service.revision += 1
        service.updated_at = utc_now()
        self._save_service(service)
        return service

    def deactivate_service(self, service_id: str) -> ServiceDefinition:
        service = self._load_service(service_id)
        service.enabled = False
        service.revision += 1
        service.updated_at = utc_now()
        self._save_service(service)
        return service

    def set_default(self, service_id: str) -> ServiceDefinition:
        service = self._load_service(service_id)
        # 原子取消同 capability 旧默认
        for other in self._list_all():
            if other.capability == service.capability and other.is_default and other.service_id != service_id:
                other.is_default = False
                other.revision += 1
                other.updated_at = utc_now()
                self._save_service(other)
        service.is_default = True
        service.revision += 1
        service.updated_at = utc_now()
        self._save_service(service)
        return service

    def get_default(self, capability: str) -> ServiceDefinition | None:
        candidates = self.list_services(capability=capability, enabled=True)
        # is_default first, then priority ASC
        defaults = [s for s in candidates if s.is_default]
        if defaults:
            return defaults[0]
        return candidates[0] if candidates else None

    def probe_service(self, service_id: str) -> dict[str, Any]:
        service = self._load_service(service_id)
        start = time.monotonic()
        try:
            available, error_code, suggestion = self._do_probe(service)
        except Exception as exc:
            available, error_code, suggestion = False, "PROBE_ERROR", str(exc)[:200]
        latency_ms = round((time.monotonic() - start) * 1000)
        return {
            "available": available,
            "checked_at": utc_now(),
            "latency_ms": latency_ms,
            "component": service.service_id,
            "error_code": error_code,
            "suggestion": suggestion,
        }

    def _do_probe(self, service: ServiceDefinition) -> tuple[bool, str | None, str | None]:
        """根据 adapter_type 执行真实轻量检查。"""
        # 检查 required secrets
        for key in service.required_secrets:
            full_key = f"{service.service_id}_{key}"
            if not self._secret_store.get(full_key):
                return False, "SECRET_NOT_CONFIGURED", f"请配置 {key}"

        if service.adapter_type in ("openai_compatible",):
            # API 类型只检查 secret 存在
            return True, None, None

        if service.adapter_type == "indextts":
            return self._probe_tts(service)
        if service.adapter_type == "whisper":
            return self._probe_alignment(service)
        if service.adapter_type == "ffmpeg":
            return self._probe_ffmpeg()
        if service.adapter_type == "local_process":
            return self._probe_local_process(service)
        # 未知类型：默认可用
        return True, None, None

    def _probe_tts(self, service: ServiceDefinition) -> tuple[bool, str | None, str | None]:
        import shutil
        import httpx
        url = service.config.get("url", service.endpoint or "http://127.0.0.1:7860")
        mode = service.config.get("mode", "gradio")
        try:
            if mode == "fastapi":
                with httpx.Client(timeout=5) as client:
                    response = client.get(f"{url}/health")
                    if response.status_code == 200:
                        return True, None, None
            else:
                with httpx.Client(timeout=5) as client:
                    response = client.get(f"{url}/")
                    if response.status_code == 200:
                        return True, None, None
            return False, "TTS_UNREACHABLE", f"TTS 服务不可达，请确认服务已启动"
        except (httpx.ConnectError, httpx.TimeoutException):
            return False, "TTS_UNREACHABLE", f"TTS 服务不可达，请确认服务已启动"

    def _probe_alignment(self, service: ServiceDefinition) -> tuple[bool, str | None, str | None]:
        import shutil
        mode = service.config.get("mode", "node")
        if mode == "node":
            node = shutil.which("node")
            if not node:
                return False, "NODE_NOT_FOUND", "请安装 Node.js"
            renderer_root = self._data_dir.parent / "video_renderer"
            align_script = renderer_root / "align.mjs"
            if not align_script.exists():
                return False, "ALIGN_SCRIPT_NOT_FOUND", "对齐脚本不存在"
            return True, None, None
        else:
            import httpx
            url = service.config.get("base_url", service.endpoint or "http://127.0.0.1:9000")
            try:
                with httpx.Client(timeout=5) as client:
                    response = client.get(f"{url}/health")
                    if response.status_code == 200:
                        return True, None, None
                return False, "WHISPER_UNREACHABLE", "Whisper 服务不可达"
            except (httpx.ConnectError, httpx.TimeoutException):
                return False, "WHISPER_UNREACHABLE", "Whisper 服务不可达"

    def _probe_ffmpeg(self) -> tuple[bool, str | None, str | None]:
        import shutil
        if not shutil.which("ffmpeg"):
            return False, "FFMPEG_NOT_FOUND", "请安装 FFmpeg"
        if not shutil.which("ffprobe"):
            return False, "FFPROBE_NOT_FOUND", "请安装 FFmpeg (包含 ffprobe)"
        return True, None, None

    def _probe_local_process(self, service: ServiceDefinition) -> tuple[bool, str | None, str | None]:
        import shutil
        script = service.config.get("script", "")
        if script:
            script_path = self._data_dir.parent / script
            if not script_path.exists():
                return False, "SCRIPT_NOT_FOUND", f"脚本不存在"
        return True, None, None

    def list_secrets(self, service_id: str) -> list[dict[str, Any]]:
        service = self._load_service(service_id)
        result = []
        now = utc_now()
        for key in service.required_secrets + service.optional_secrets:
            full_key = f"{service_id}_{key}"
            value = self._secret_store.get(full_key)
            result.append({
                "secret_key": key,
                "configured": value is not None,
                "masked_value": mask_secret(value) if value else "",
                "updated_at": now,
            })
        return result

    def set_secret(self, service_id: str, secret_key: str, secret_value: str) -> None:
        service = self._load_service(service_id)
        allowed_keys = set(service.required_secrets + service.optional_secrets)
        if secret_key not in allowed_keys:
            raise DomainError("VALIDATION_ERROR", f"不允许设置未知 secret: {secret_key}")
        full_key = f"{service_id}_{secret_key}"
        self._secret_store.set(full_key, secret_value)

    def delete_secret(self, service_id: str, secret_key: str) -> None:
        service = self._load_service(service_id)
        full_key = f"{service_id}_{secret_key}"
        self._secret_store.delete(full_key)

    def get_secret_value(self, service_id: str, secret_key: str) -> str | None:
        """内部使用：获取 secret 值。不暴露给 API。"""
        full_key = f"{service_id}_{secret_key}"
        return self._secret_store.get(full_key)
