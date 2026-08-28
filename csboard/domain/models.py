from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from csboard.domain.enums import Engine, Entrypoint, ProjectStatus, RunStatus, StageStatus


@dataclass(slots=True)
class Project:
    project_id: str
    title: str
    pipeline_id: str
    engine: Engine
    status: ProjectStatus
    created_at: str
    updated_at: str
    active_run_id: str | None = None
    revision: int = 1
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Project":
        return cls(
            project_id=str(value["project_id"]),
            title=str(value["title"]),
            pipeline_id=str(value["pipeline_id"]),
            engine=Engine(value["engine"]),
            status=ProjectStatus(value["status"]),
            created_at=str(value["created_at"]),
            updated_at=str(value["updated_at"]),
            active_run_id=value.get("active_run_id"),
            revision=int(value.get("revision", 1)),
            schema_version=int(value.get("schema_version", 1)),
        )


@dataclass(slots=True)
class StageState:
    status: StageStatus = StageStatus.PENDING
    attempt: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status.value, "attempt": self.attempt}


@dataclass(slots=True)
class Run:
    run_id: str
    project_id: str
    trace_id: str
    entrypoint: Entrypoint
    command_ids: list[str]
    status: RunStatus
    target_stage: str
    started_at: str
    finished_at: str | None = None
    stages: dict[str, StageState] = field(default_factory=dict)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "project_id": self.project_id,
            "trace_id": self.trace_id,
            "entrypoint": self.entrypoint.value,
            "command_ids": self.command_ids,
            "status": self.status.value,
            "target_stage": self.target_stage,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "stages": {name: state.to_dict() for name, state in self.stages.items()},
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Run":
        stages = {
            str(name): StageState(StageStatus(item["status"]), int(item["attempt"]))
            for name, item in dict(value.get("stages", {})).items()
        }
        return cls(
            run_id=str(value["run_id"]),
            project_id=str(value["project_id"]),
            trace_id=str(value["trace_id"]),
            entrypoint=Entrypoint(value["entrypoint"]),
            command_ids=[str(item) for item in value["command_ids"]],
            status=RunStatus(value["status"]),
            target_stage=str(value["target_stage"]),
            started_at=str(value["started_at"]),
            finished_at=value.get("finished_at"),
            stages=stages,
            warnings=list(value.get("warnings", [])),
            schema_version=int(value.get("schema_version", 1)),
        )


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    artifact_key: str
    relative_path: str
    sha256: str
    size_bytes: int
    producer_stage: str
    status: str = "succeeded"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
