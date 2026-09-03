from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from csboard.domain.errors import DomainError


CANONICAL_STAGES = (
    "generate-visual-anchors",
    "clone-voice",
    "plan-storyboard",
    "generate-illustrations",
    "render-visuals",
    "compose-video",
)
_STAGE_INDEX = {name: index for index, name in enumerate(CANONICAL_STAGES)}


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    mode: str = "auto"
    manual_stages: tuple[str, ...] = ()

    @classmethod
    def create(cls, mode: str = "auto", manual_stages: Any = ()) -> "ExecutionPlan":
        if mode not in {"auto", "selective"}:
            raise DomainError("VALIDATION_ERROR", "execution_mode 必须是 auto 或 selective")
        if not isinstance(manual_stages, (list, tuple)):
            raise DomainError("VALIDATION_ERROR", "manual_stages 必须是数组")
        stages = list(manual_stages)
        if any(not isinstance(stage, str) or not stage for stage in stages):
            raise DomainError("VALIDATION_ERROR", "manual_stages 包含非法阶段")
        if len(set(stages)) != len(stages):
            raise DomainError("VALIDATION_ERROR", "manual_stages 不得重复")
        unknown = [stage for stage in stages if stage not in _STAGE_INDEX]
        if unknown:
            raise DomainError("VALIDATION_ERROR", "manual_stages 包含未知阶段")
        stages.sort(key=_STAGE_INDEX.__getitem__)
        if mode == "auto" and stages:
            raise DomainError("VALIDATION_ERROR", "auto 模式的 manual_stages 必须为空")
        if mode == "selective" and not stages:
            raise DomainError("VALIDATION_ERROR", "selective 模式至少需要一个手动阶段")
        return cls(mode=mode, manual_stages=tuple(stages))

    @classmethod
    def from_dict(cls, value: Any) -> "ExecutionPlan":
        if not isinstance(value, dict):
            raise DomainError("VALIDATION_ERROR", "execution_plan 必须是对象")
        return cls.create(value.get("mode", "auto"), value.get("manual_stages", []))

    def to_dict(self) -> dict[str, Any]:
        return {"mode": self.mode, "manual_stages": list(self.manual_stages)}
