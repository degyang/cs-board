from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class DomainError(RuntimeError):
    code: str
    message: str
    retryable: bool = False
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


class NotFoundError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__("NOT_FOUND", message)


class InvalidStateTransition(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_STATE_TRANSITION", message)


class InvalidArtifactPath(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_ARTIFACT_PATH", message)
