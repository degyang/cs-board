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
    language: str = "und"
    emotion_mode: str = "speaker"
    example_text: str = ""
    availability_status: str = "available"
    status_note: str = ""
    engine: str = "unknown"
    emotion_weight: float | None = None
    emotion_reference_asset_id: str = ""
    source: str = ""
    compatibility: dict[str, Any] = field(default_factory=lambda: {
        "engines": ["unknown"], "emotion_modes": ["speaker"], "limitations": [],
    })

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
            language=str(value.get("language", "und")),
            emotion_mode=str(value.get("emotion_mode", "speaker")),
            example_text=str(value.get("example_text", "")),
            availability_status=str(value.get("availability_status", "available")),
            status_note=str(value.get("status_note", "")),
            engine=str(value.get("engine", "unknown")),
            emotion_weight=(float(value["emotion_weight"]) if value.get("emotion_weight") is not None else None),
            emotion_reference_asset_id=str(value.get("emotion_reference_asset_id", "")),
            source=str(value.get("source", "")),
            compatibility=dict(value.get("compatibility") or {
                "engines": ["unknown"], "emotion_modes": ["speaker"], "limitations": [],
            }),
        )
