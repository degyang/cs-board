"""ServiceDefinition — 动态服务注册领域模型。

运行时注册表不依赖 PROVIDER_PROFILES。
同一 capability 必须允许注册多个服务。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ServiceDefinition:
    """服务定义。"""

    schema_version: int = 1
    revision: int = 1
    service_id: str = ""
    display_name: str = ""
    capability: str = ""  # text_generation, image_generation, speech_synthesis, speech_alignment, rendering, media, codex_skill, ...
    adapter_type: str = ""  # openai_compatible, indextts, whisper, ffmpeg, local_process, codex_skill, ...
    endpoint: str = ""
    model: str = ""
    enabled: bool = True
    priority: int = 100
    is_default: bool = False
    config: dict[str, Any] = field(default_factory=dict)
    required_secrets: list[str] = field(default_factory=list)
    optional_secrets: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ServiceDefinition:
        return cls(
            schema_version=int(value.get("schema_version", 1)),
            revision=int(value.get("revision", 1)),
            service_id=str(value.get("service_id", "")),
            display_name=str(value.get("display_name", "")),
            capability=str(value.get("capability", "")),
            adapter_type=str(value.get("adapter_type", "")),
            endpoint=str(value.get("endpoint", "")),
            model=str(value.get("model", "")),
            enabled=bool(value.get("enabled", True)),
            priority=int(value.get("priority", 100)),
            is_default=bool(value.get("is_default", False)),
            config=dict(value.get("config", {})),
            required_secrets=[str(s) for s in value.get("required_secrets", [])],
            optional_secrets=[str(s) for s in value.get("optional_secrets", [])],
            created_at=str(value.get("created_at", "")),
            updated_at=str(value.get("updated_at", "")),
        )

    def to_public_dict(self) -> dict[str, Any]:
        """返回不含 config 中敏感字段的公开字典。"""
        d = self.to_dict()
        return d
