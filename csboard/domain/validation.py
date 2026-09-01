from __future__ import annotations

import re

from csboard.domain.errors import DomainError


def validate_state_transition(current: str, target: str, allowed: dict[str, set[str]]) -> None:
    if current == target:
        return
    if target not in allowed.get(current, set()):
        raise DomainError("INVALID_STATE_TRANSITION", f"非法状态转换：{current} → {target}")


def validate_relative_path(value: str) -> None:
    if (
        not value
        or value.startswith(("/", "\\"))
        or "\\" in value
        or re.match(r"^[a-zA-Z]:", value)
        or ".." in value.split("/")
    ):
        raise DomainError("INVALID_ARTIFACT_PATH", "Artifact 路径必须是任务内相对路径")
