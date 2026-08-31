"""VoiceAsset — 语音资产领域模型。

通过 MediaPort 的 probe() 校验。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class VoiceAsset:
    """语音资产。"""

    voice_id: str
    name: str
    storage_path: str  # 相对路径
    duration_ms: int
    sample_rate: int
    channels: int
    format: str  # "wav" | "mp3"
    sha256: str
    created_at: str
    is_active: bool = True
    tags: list[str] = field(default_factory=list)
    revision: int = 1
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> VoiceAsset:
        return cls(
            voice_id=str(value["voice_id"]),
            name=str(value["name"]),
            storage_path=str(value["storage_path"]),
            duration_ms=int(value["duration_ms"]),
            sample_rate=int(value["sample_rate"]),
            channels=int(value["channels"]),
            format=str(value["format"]),
            sha256=str(value["sha256"]),
            created_at=str(value.get("created_at", "")),
            is_active=bool(value.get("is_active", True)),
            tags=list(value.get("tags", [])),
            revision=int(value.get("revision", 1)),
            updated_at=str(value.get("updated_at", "")),
        )
