"""FilesystemServiceRegistry — 文件系统服务注册表实现。

数据位置：<data_dir>/settings/services/*.json
运行时不依赖 PROVIDER_PROFILES。
"""

from __future__ import annotations

import re
import time
import uuid
import json
from pathlib import Path
from typing import Any

from csboard.adapters.secrets import SecretStoreProtocol, mask_secret
from csboard.application.context import utc_now
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.service_definition import ServiceDefinition

# service_id 校验
_SERVICE_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")
_FORBIDDEN_ID_PATTERNS = ["..", "/", "\\"]

# PATCH 允许的字段白名单
_PATCHABLE_FIELDS = {
    "display_name", "endpoint", "model", "enabled", "priority",
    "config", "required_secrets", "optional_secrets",
}

# config 中敏感字段（大小写不敏感）
_SENSITIVE_CONFIG_KEYS = {
    "api_key", "key", "token", "secret", "password", "credential",
    "authorization", "access_token", "refresh_token", "api_secret",
}


def _validate_service_id(service_id: str) -> None:
    """校验 service_id 格式。"""
    if not service_id:
        raise DomainError("VALIDATION_ERROR", "service_id 不能为空")
    if len(service_id) > 64:
        raise DomainError("VALIDATION_ERROR", "service_id 不能超过 64 字符")
    for pat in _FORBIDDEN_ID_PATTERNS:
        if pat in service_id:
            raise DomainError("VALIDATION_ERROR", f"service_id 包含非法字符: {pat}")
    if not _SERVICE_ID_RE.match(service_id):
        raise DomainError("VALIDATION_ERROR", f"service_id 格式不合法: {service_id}")


def _sanitize_config(config: dict[str, Any]) -> dict[str, Any]:
    """过滤 config 中的敏感字段。"""
    return {k: v for k, v in config.items() if k.lower() not in _SENSITIVE_CONFIG_KEYS}


def _validate_create(service: ServiceDefinition) -> None:
    """创建时校验。"""
    _validate_service_id(service.service_id)
    if not service.display_name:
        raise DomainError("VALIDATION_ERROR", "display_name 不能为空")
    if not service.capability:
        raise DomainError("VALIDATION_ERROR", "capability 不能为空")
    if not service.adapter_type:
        raise DomainError("VALIDATION_ERROR", "adapter_type 不能为空")
    if not isinstance(service.priority, int) or service.priority < 0:
        raise DomainError("VALIDATION_ERROR", "priority 必须是非负整数")
    if not isinstance(service.required_secrets, list):
        raise DomainError("VALIDATION_ERROR", "required_secrets 必须是字符串数组")
    if not isinstance(service.optional_secrets, list):
        raise DomainError("VALIDATION_ERROR", "optional_secrets 必须是字符串数组")
    if not isinstance(service.config, dict):
        raise DomainError("VALIDATION_ERROR", "config 必须是对象")


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
        except (json.JSONDecodeError, OSError):
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

    def list_services(
        self,
        capability: str | None = None,
        enabled: bool | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> list[ServiceDefinition]:
        """列出服务，支持 capability/enabled 过滤和分页。"""
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

        # cursor: skip until cursor found
        if cursor:
            cursor_idx = -1
            for idx, s in enumerate(filtered):
                if s.service_id == cursor:
                    cursor_idx = idx + 1
                    break
            if cursor_idx > 0:
                filtered = filtered[cursor_idx:]

        if limit is not None:
            filtered = filtered[:max(1, min(limit, 100))]

        return filtered

    def get_service(self, service_id: str) -> ServiceDefinition:
        return self._load_service(service_id)

    def create_service(self, service: ServiceDefinition) -> ServiceDefinition:
        _validate_create(service)
        if self._service_path(service.service_id).exists():
            raise DomainError("CONFLICT", f"服务 '{service.service_id}' 已存在")
        now = utc_now()
        service.created_at = now
        service.updated_at = now
        service.revision = 1
        # 如果是第一个同 capability 的服务，自动设为默认
        existing = self.list_services(capability=service.capability, enabled=True)
        if not existing:
            service.is_default = True
        # 如果设为默认，取消同 capability 其他默认
        if service.is_default:
            for other in self._list_all():
                if other.capability == service.capability and other.is_default:
                    other.is_default = False
                    other.revision += 1
                    other.updated_at = now
                    self._save_service(other)
        self._save_service(service)
        return service

    def update_service(
        self,
        service_id: str,
        updates: dict[str, Any],
        expected_revision: int | None = None,
    ) -> ServiceDefinition:
        service = self._load_service(service_id)

        # revision 冲突检查
        if expected_revision is not None and service.revision != expected_revision:
            raise DomainError(
                "REVISION_CONFLICT",
                f"revision 冲突: 期望 {expected_revision}，实际 {service.revision}",
            )

        # 字段白名单
        unknown = set(updates.keys()) - _PATCHABLE_FIELDS
        if unknown:
            raise DomainError("VALIDATION_ERROR", f"不允许更新字段: {', '.join(sorted(unknown))}")

        for key, value in updates.items():
            if key == "enabled":
                service.enabled = bool(value)
            elif key == "priority":
                if not isinstance(value, int) or value < 0:
                    raise DomainError("VALIDATION_ERROR", "priority 必须是非负整数")
                service.priority = value
            elif key == "config":
                if not isinstance(value, dict):
                    raise DomainError("VALIDATION_ERROR", "config 必须是对象")
                service.config = value
            elif key == "required_secrets":
                if not isinstance(value, list):
                    raise DomainError("VALIDATION_ERROR", "required_secrets 必须是字符串数组")
                service.required_secrets = value
            elif key == "optional_secrets":
                if not isinstance(value, list):
                    raise DomainError("VALIDATION_ERROR", "optional_secrets 必须是字符串数组")
                service.optional_secrets = value
            elif hasattr(service, key):
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
        # 停用默认服务时自动清除默认标记
        if service.is_default:
            service.is_default = False
        service.revision += 1
        service.updated_at = utc_now()
        self._save_service(service)
        return service

    def set_default(self, service_id: str) -> ServiceDefinition:
        service = self._load_service(service_id)
        if not service.enabled:
            raise DomainError("CONFLICT", "不能将停用的服务设为默认")
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
        defaults = [s for s in candidates if s.is_default]
        if defaults:
            return defaults[0]
        return candidates[0] if candidates else None

    def probe_service(self, service_id: str) -> dict[str, Any]:
        service = self._load_service(service_id)
        start = time.monotonic()
        try:
            available, error_code, suggestion = self._do_probe(service)
        except Exception:
            available, error_code, suggestion = False, "PROBE_ERROR", "探测时发生内部错误"
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
        for key in service.required_secrets:
            full_key = f"{service.service_id}_{key}"
            if not self._secret_store.get(full_key):
                return False, "SECRET_NOT_CONFIGURED", f"请配置 {key}"

        if service.adapter_type == "openai_compatible":
            return self._probe_openai(service)
        if service.adapter_type == "indextts":
            return self._probe_tts(service)
        if service.adapter_type == "whisper":
            return self._probe_alignment(service)
        if service.adapter_type == "ffmpeg":
            return self._probe_ffmpeg()
        if service.adapter_type == "local_process":
            return self._probe_local_process(service)
        # 未知 adapter
        return False, "UNSUPPORTED_ADAPTER", f"不支持的 adapter_type: {service.adapter_type}"

    def _probe_openai(self, service: ServiceDefinition) -> tuple[bool, str | None, str | None]:
        """OpenAI-compatible 探测：短超时请求 /models。"""
        import httpx
        endpoint = service.endpoint or "https://api.openai.com/v1"
        api_key = self._secret_store.get(f"{service.service_id}_api_key")
        if not api_key:
            return False, "SECRET_NOT_CONFIGURED", "请配置 api_key"
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(
                    f"{endpoint}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if response.status_code == 200:
                    return True, None, None
                if response.status_code == 401:
                    return False, "AUTH_FAILED", "API Key 无效"
                return False, "OPENAI_UNEXPECTED_STATUS", f"服务返回状态码 {response.status_code}"
        except httpx.ConnectError:
            return False, "OPENAI_UNREACHABLE", "服务不可达"
        except httpx.TimeoutException:
            return False, "OPENAI_TIMEOUT", "服务响应超时"
        except Exception:
            return False, "OPENAI_PROBE_ERROR", "探测时发生错误"

    def _probe_tts(self, service: ServiceDefinition) -> tuple[bool, str | None, str | None]:
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
            return False, "TTS_UNREACHABLE", "TTS 服务不可达，请确认服务已启动"
        except (httpx.ConnectError, httpx.TimeoutException):
            return False, "TTS_UNREACHABLE", "TTS 服务不可达，请确认服务已启动"

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
        script = service.config.get("script", "")
        if script:
            script_path = self._data_dir.parent / script
            if not script_path.exists():
                return False, "SCRIPT_NOT_FOUND", "脚本不存在"
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

    def to_public_dict(self, service: ServiceDefinition) -> dict[str, Any]:
        """返回脱敏的公开 DTO。"""
        data = service.to_dict()
        data["config"] = _sanitize_config(service.config)
        return data
