"""Read-only Precondition asset view.

Preconditions are reusable runtime constraints, not Task selections or Style
characters.  Selection, Run snapshots, revisions and uploads deliberately
remain outside this first read-only catalog slice.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


VALID_PRECONDITION_KINDS = frozenset({"visual-explainer", "renderer-hand"})


@dataclass(slots=True)
class Precondition:
    precondition_id: str
    revision: int
    name: str
    kind: str
    applies_to: list[str]
    status: str = "active"
    enabled: bool = True
    engine_compatibility: list[str] = field(default_factory=list)
    preview_asset_id: str = ""
    description: str = ""
    condition_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Precondition":
        kind = str(value["kind"])
        if kind not in VALID_PRECONDITION_KINDS:
            raise ValueError(f"unsupported precondition kind: {kind}")
        applies_to = [str(stage) for stage in value["applies_to"]]
        if not applies_to:
            raise ValueError("precondition applies_to cannot be empty")
        return cls(
            precondition_id=str(value["precondition_id"]),
            revision=int(value.get("revision", 1)),
            name=str(value["name"]),
            kind=kind,
            applies_to=applies_to,
            status=str(value.get("status", "active")),
            enabled=bool(value.get("enabled", True)),
            engine_compatibility=[str(engine) for engine in value.get("engine_compatibility", [])],
            preview_asset_id=str(value.get("preview_asset_id", "")),
            description=str(value.get("description", "")),
            condition_text=str(value.get("condition_text", "")),
        )
