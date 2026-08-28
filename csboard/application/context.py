from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from csboard.domain.enums import Entrypoint


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


@dataclass(frozen=True, slots=True)
class CommandContext:
    entrypoint: Entrypoint
    command_id: str = field(default_factory=lambda: new_id("command"))
    actor_type: str = "local-user"
    actor_id: str | None = None
    occurred_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)
