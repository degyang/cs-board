"""ServiceResolver — 按 capability 从动态注册表选择服务。"""

from __future__ import annotations

from typing import Any

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.domain.errors import DomainError
from csboard.domain.service_definition import ServiceDefinition


# Stage → capability 映射
STAGE_CAPABILITY_MAP: dict[str, str] = {
    "generate-visual-anchors": "text_generation",
    "clone-voice": "speech_synthesis",
    "plan-storyboard": "text_generation",
    "generate-illustrations": "image_generation",
    "render-visuals": "rendering",
    "compose-video": "media",
}

# alignment 不是 stage，但需要 capability 映射
EXTRA_CAPABILITY_MAP: dict[str, str] = {
    "alignment": "speech_alignment",
}


class ServiceResolver:
    """按 capability 从 ServiceRegistry 选择最优服务。"""

    def __init__(self, registry: FilesystemServiceRegistry) -> None:
        self._registry = registry

    def resolve(self, capability: str) -> ServiceDefinition:
        """选择指定 capability 的最优启用服务。

        规则：
        1. capability 匹配
        2. enabled=true
        3. is_default=true 优先
        4. priority 升序
        5. service_id 稳定排序

        无可用服务时抛出 CAPABILITY_NOT_AVAILABLE。
        """
        services = [
            service for service in self._registry.list_services(capability=capability, enabled=True)
            if self._registry.has_required_secrets(service)
        ]
        if not services:
            raise DomainError(
                "CAPABILITY_NOT_AVAILABLE",
                f"没有可用的 {capability} 服务",
                details={"capability": capability},
            )

        # 排序：is_default 降序 → priority 升序 → service_id 升序
        services.sort(
            key=lambda s: (
                not s.is_default,
                s.priority,
                s.service_id,
            )
        )
        return services[0]

    def resolve_for_stage(self, stage_name: str) -> ServiceDefinition:
        """按 stage 名称选择服务。"""
        capability = STAGE_CAPABILITY_MAP.get(stage_name)
        if not capability:
            raise DomainError(
                "CAPABILITY_NOT_AVAILABLE",
                f"阶段 {stage_name} 没有 capability 映射",
                details={"stage": stage_name},
            )
        return self.resolve(capability)

    def resolve_tts(self) -> ServiceDefinition:
        """选择 TTS 服务。"""
        return self.resolve("speech_synthesis")

    def resolve_alignment(self) -> ServiceDefinition:
        """选择对齐服务。"""
        return self.resolve("speech_alignment")

    def resolve_text_model(self) -> ServiceDefinition:
        """选择文本模型服务。"""
        return self.resolve("text_generation")

    def resolve_image_model(self) -> ServiceDefinition:
        """选择图像模型服务。"""
        return self.resolve("image_generation")

    def resolve_renderer(self) -> ServiceDefinition:
        """选择渲染服务。"""
        return self.resolve("rendering")

    def resolve_media(self) -> ServiceDefinition:
        """选择媒体处理服务。"""
        return self.resolve("media")
