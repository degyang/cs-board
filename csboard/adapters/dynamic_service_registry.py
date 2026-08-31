"""DynamicServiceRegistry — 动态服务注册表。

继承 ProviderFactory 的能力，扩展为动态注册。
adapter_type 决定 config 字段白名单。
"""

from __future__ import annotations

import shutil
from typing import Any

from csboard.adapters.provider_factory import ProviderFactory
from csboard.adapters.secrets import SecretStoreProtocol, mask_secret
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.provider_types import PROVIDER_PROFILES, ProviderType


class DynamicServiceRegistry:
    """动态服务注册表。"""

    def __init__(self, provider_factory: ProviderFactory) -> None:
        self._providers = provider_factory

    def list_services(self) -> list[dict[str, Any]]:
        """列出所有服务。"""
        result = []
        for name, profile in PROVIDER_PROFILES.items():
            config_status = self._providers.check_provider(name)
            availability = self._providers.check_provider_availability(name)
            result.append({
                "service_id": name,
                "adapter_type": profile.provider_type.value,
                "display_name": profile.name,
                "description": profile.description,
                "config": profile.config,
                "config_status": config_status,
                "availability": availability,
            })
        return result

    def get_service(self, service_id: str) -> dict[str, Any]:
        """获取单个服务状态。"""
        profile = PROVIDER_PROFILES.get(service_id)
        if profile is None:
            raise NotFoundError(f"服务 '{service_id}' 不存在")
        config_status = self._providers.check_provider(service_id)
        availability = self._providers.check_provider_availability(service_id)
        return {
            "service_id": service_id,
            "adapter_type": profile.provider_type.value,
            "display_name": profile.name,
            "description": profile.description,
            "config": profile.config,
            "config_status": config_status,
            "availability": availability,
        }

    def _get_allowed_config_keys(self, service_id: str) -> set[str]:
        """获取服务允许配置的字段白名单。"""
        from csboard.domain.provider_types import PROVIDER_PROFILES
        profile = PROVIDER_PROFILES.get(service_id)
        if profile is None:
            raise NotFoundError(f"服务 '{service_id}' 不存在")
        return set(profile.config.keys())

    def update_service_config(self, service_id: str, config: dict[str, Any]) -> None:
        """更新服务配置（仅白名单字段）。"""
        allowed_keys = self._get_allowed_config_keys(service_id)
        unknown_keys = set(config.keys()) - allowed_keys
        if unknown_keys:
            raise DomainError(
                "VALIDATION_ERROR",
                f"不允许更新未知字段: {', '.join(sorted(unknown_keys))}。"
                f"允许的字段: {', '.join(sorted(allowed_keys))}",
            )
        self._providers.update_profile_config(service_id, config)

    def set_service_secret(self, service_id: str, secret_key: str, secret_value: str) -> None:
        """设置服务 Secret。"""
        profile = PROVIDER_PROFILES.get(service_id)
        if profile is None:
            raise NotFoundError(f"服务 '{service_id}' 不存在")
        allowed_keys = set(profile.required_secrets + profile.optional_secrets)
        if secret_key not in allowed_keys:
            raise DomainError(
                "VALIDATION_ERROR",
                f"不允许设置未知 secret: {secret_key}。"
                f"允许的 secret: {', '.join(sorted(allowed_keys))}",
            )
        full_key = f"{profile.provider_type.value}_{secret_key}"
        self._providers.secret_store.set(full_key, secret_value)

    def check_health(self, service_id: str) -> dict[str, Any]:
        """检查服务健康状态。"""
        profile = PROVIDER_PROFILES.get(service_id)
        if profile is None:
            raise NotFoundError(f"服务 '{service_id}' 不存在")
        return self._providers.check_provider_availability(service_id)

    def check_all_health(self) -> dict[str, Any]:
        """检查所有服务健康状态。"""
        return self._providers.check_all_availability()

    def get_runtime_status(self) -> dict[str, Any]:
        """获取运行环境状态。"""
        toolchain = self._check_toolchain()
        storage = self._check_storage()
        return {
            "toolchain": toolchain,
            "storage": storage,
            "services": self.check_all_health(),
        }

    def _check_toolchain(self) -> dict[str, Any]:
        """检查工具链状态。"""
        python = shutil.which("python3") or shutil.which("python")
        node = shutil.which("node")
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        return {
            "python": {"available": bool(python), "path": python},
            "node": {"available": bool(node), "path": node},
            "ffmpeg": {"available": bool(ffmpeg), "path": ffmpeg},
            "ffprobe": {"available": bool(ffprobe), "path": ffprobe},
        }

    def _check_storage(self) -> dict[str, Any]:
        """检查存储状态。"""
        data_dir = self._providers._data_dir
        assets_dir = data_dir / "assets"
        tasks_dir = data_dir / "tasks"
        return {
            "data_dir": str(data_dir),
            "assets_dir_exists": assets_dir.exists(),
            "tasks_dir_exists": tasks_dir.exists(),
        }

    def get_voice_alignment_status(self) -> dict[str, Any]:
        """获取语音对齐状态。"""
        profile = PROVIDER_PROFILES.get("alignment")
        if profile is None:
            return {"available": False, "error_code": "PROFILE_NOT_FOUND"}
        availability = self._providers.check_provider_availability("alignment")
        return availability
