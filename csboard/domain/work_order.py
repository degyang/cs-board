from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from csboard.domain.errors import DomainError
from csboard.domain.validation import validate_relative_path, validate_state_transition


WORK_ORDER_STATUSES = frozenset({
    "ready", "waiting-manual-trigger", "running", "waiting-external-output",
    "validating", "waiting-acceptance", "succeeded", "failed", "stale",
})
STAGE_SKILLS = {
    "generate-visual-anchors": "visual-anchor-generator",
    "clone-voice": "voice-cloner",
    "plan-storyboard": "storyboard-planner",
    "generate-illustrations": "illustration-generator",
    "render-visuals": "visual-renderer",
    "compose-video": "av-compositor",
}
WORK_ORDER_TRANSITIONS = {
    "ready": {"running", "waiting-manual-trigger", "stale"},
    "waiting-manual-trigger": {"running", "stale"},
    "running": {"waiting-external-output", "validating", "succeeded", "failed", "stale"},
    "waiting-external-output": {"validating", "failed", "stale"},
    "validating": {"waiting-acceptance", "waiting-external-output", "failed", "stale"},
    "waiting-acceptance": {"succeeded", "waiting-external-output", "stale"},
    "succeeded": {"stale"},
    "failed": {"ready", "stale"},
    "stale": {"ready"},
}


def fingerprint(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class StageWorkOrder:
    schema_version: str
    work_order_id: str
    identity: dict[str, str]
    revision: int
    input_fingerprint: str
    status: str
    scope: dict[str, str]
    input_artifacts: list[dict[str, Any]]
    parameters_path: str
    instructions_path: str
    output_directory: str
    expected_outputs: list[dict[str, str]]
    commands: dict[str, list[dict[str, Any]]]
    next_action: dict[str, str]

    def __post_init__(self) -> None:
        if self.schema_version != "1.0" or not self.work_order_id or self.revision < 1:
            raise DomainError("VALIDATION_ERROR", "工作单 envelope 非法")
        stage = self.identity.get("stage")
        if stage not in STAGE_SKILLS or self.identity.get("skill") != STAGE_SKILLS[stage]:
            raise DomainError("VALIDATION_ERROR", "工作单 Stage 或 Skill 非法")
        if self.status not in WORK_ORDER_STATUSES or not self.input_fingerprint.startswith("sha256:"):
            raise DomainError("VALIDATION_ERROR", "工作单状态或 fingerprint 非法")
        if self.scope.get("kind") != "stage" or len(self.scope) != 1:
            raise DomainError("VALIDATION_ERROR", "本切片只支持 stage scope")
        for path in (self.parameters_path, self.instructions_path, self.output_directory):
            validate_relative_path(path)
        for item in self.input_artifacts:
            if item.get("status") != "succeeded" or not str(item.get("sha256", "")).startswith("sha256:"):
                raise DomainError("VALIDATION_ERROR", "工作单输入 Artifact 非法")
            validate_relative_path(str(item.get("relative_path", "")))
        if set(self.commands) != {"run", "import", "validate", "accept", "reject", "retry"}:
            raise DomainError("VALIDATION_ERROR", "工作单 commands 不完整")
        for command_list in self.commands.values():
            for command in command_list:
                argv = command.get("argv")
                if not isinstance(argv, list) or not all(isinstance(arg, str) for arg in argv):
                    raise DomainError("VALIDATION_ERROR", "工作单 argv 必须是字符串数组")
                for arg in argv:
                    if arg.startswith(("/", "\\", "~")) or ".." in arg.split("/"):
                        raise DomainError("VALIDATION_ERROR", "工作单 argv 不得包含绝对或逃逸路径")

    def transition(self, status: str) -> "StageWorkOrder":
        validate_state_transition(self.status, status, WORK_ORDER_TRANSITIONS)
        return StageWorkOrder(**{**self.to_dict(), "status": status})

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version, "work_order_id": self.work_order_id,
            "identity": self.identity, "revision": self.revision,
            "input_fingerprint": self.input_fingerprint, "status": self.status,
            "scope": self.scope, "input_artifacts": self.input_artifacts,
            "parameters_path": self.parameters_path, "instructions_path": self.instructions_path,
            "output_directory": self.output_directory, "expected_outputs": self.expected_outputs,
            "commands": self.commands, "next_action": self.next_action,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "StageWorkOrder":
        return cls(**{key: value[key] for key in (
            "schema_version", "work_order_id", "identity", "revision", "input_fingerprint", "status",
            "scope", "input_artifacts", "parameters_path", "instructions_path", "output_directory",
            "expected_outputs", "commands", "next_action")})
