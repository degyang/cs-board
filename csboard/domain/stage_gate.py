"""Persistent human-review gates for the phase-one manual stage path."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from csboard.domain.errors import DomainError
from csboard.domain.execution_plan import CANONICAL_STAGES

GATE_NOT_READY = "not-ready"
GATE_WAITING = "waiting-review"
GATE_APPROVED = "approved"
GATE_REJECTED = "rejected"
GATE_REDO = "redo-required"

@dataclass(frozen=True, slots=True)
class StageGate:
    task_id: str; run_id: str; trace_id: str; stage_id: str
    status: str = GATE_NOT_READY; decision: str | None = None; actor: str | None = None
    decided_at: str | None = None; attempt: int = 0; revision: int = 0
    evidence: tuple[dict[str, str], ...] = ()
    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "run_id": self.run_id, "trace_id": self.trace_id, "stage_id": self.stage_id, "status": self.status, "decision": self.decision, "actor": self.actor, "decided_at": self.decided_at, "attempt": self.attempt, "revision": self.revision, "evidence": list(self.evidence)}
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StageGate": return cls(**{**data, "evidence": tuple(data.get("evidence", []))})
    @classmethod
    def initial(cls, task_id: str, run_id: str, trace_id: str, stage_id: str) -> "StageGate":
        if stage_id not in CANONICAL_STAGES: raise DomainError("VALIDATION_ERROR", "未知 Stage")
        return cls(task_id, run_id, trace_id, stage_id)
