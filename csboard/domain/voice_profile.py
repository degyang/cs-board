"""Provider-neutral remote voice and speaking-style profiles."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


VOICE_PROFILE_KINDS = frozenset({"provider-preset", "provider-designed"})


@dataclass(frozen=True, slots=True)
class VoiceStyleProfile:
    style_profile_id: str
    revision: int
    name: str
    provider_id: str | None
    instruction: str
    tags: tuple[str, ...] = ()
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["tags"] = list(self.tags)
        return value


@dataclass(frozen=True, slots=True)
class VoiceProfile:
    profile_id: str
    revision: int
    name: str
    kind: str
    provider_id: str
    model_id: str
    vendor_id: str | None = None
    vendor_name: str | None = None
    remote_voice_id: str | None = None
    design_prompt: str | None = None
    default_style_profile_id: str | None = None
    language: str | None = None
    gender: str | None = None
    tags: tuple[str, ...] = ()
    status: str = "active"
    capability_snapshot: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in VOICE_PROFILE_KINDS:
            raise ValueError(f"unsupported voice profile kind: {self.kind}")
        if self.kind == "provider-preset" and not self.remote_voice_id:
            raise ValueError("provider-preset requires remote_voice_id")
        if self.kind == "provider-designed" and not self.design_prompt:
            raise ValueError("provider-designed requires design_prompt")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["tags"] = list(self.tags)
        return value
