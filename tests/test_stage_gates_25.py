from __future__ import annotations
from pathlib import Path
import pytest
from csboard.adapters.filesystem import FilesystemArtifactStore
from tests.test_stage_gates_24 import _commands
from csboard.domain.errors import DomainError
from csboard.domain.execution_plan import CANONICAL_STAGES

def test_approval_requires_current_artifact_hash(tmp_path: Path) -> None:
    commands, task_id, run_id = _commands(tmp_path)
    commands.mark_gate_waiting(task_id, run_id, CANONICAL_STAGES[0])
    ref = FilesystemArtifactStore(commands.repository).commit_bytes(task_id, run_id, "planning.av-plan", "planning/av-plan.json", b"current", CANONICAL_STAGES[0])
    with pytest.raises(DomainError):
        commands.decide_gate(task_id, run_id, CANONICAL_STAGES[0], "approve", "reviewer", evidence=[{"logical_key": ref.artifact_key, "sha256": "wrong"}])

def test_strict_evidence_rejects_unknown_fields(tmp_path: Path) -> None:
    commands, task_id, run_id = _commands(tmp_path)
    commands.mark_gate_waiting(task_id, run_id, CANONICAL_STAGES[0])
    with pytest.raises(DomainError):
        commands.decide_gate(task_id, run_id, CANONICAL_STAGES[0], "approve", "reviewer", evidence=[{"logical_key": "x", "sha256": "y", "secret": "no"}])
