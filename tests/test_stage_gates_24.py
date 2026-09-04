from __future__ import annotations
from pathlib import Path

import pytest

from csboard.adapters.filesystem.repository import FilesystemTaskRepository
from csboard.adapters.filesystem import FilesystemArtifactStore
from csboard.application.commands import MountainCommands
from csboard.application.context import CommandContext, utc_now
from csboard.domain.enums import Engine, Entrypoint, RunStatus, TaskStatus
from csboard.domain.errors import DomainError
from csboard.domain.execution_plan import CANONICAL_STAGES
from csboard.domain.models import Run, Task


def _commands(root: Path) -> tuple[MountainCommands, str, str]:
    commands = MountainCommands(root)
    task = Task("task-gate", "gate", "mountain-av-v1", Engine.WHITEBOARD, TaskStatus.READY, utc_now(), utc_now(), active_run_id="run-gate")
    run = Run("run-gate", "task-gate", "trace-gate", Entrypoint.CLI, [], RunStatus.PENDING, "compose-video", utc_now())
    commands.repository.create_task(task); commands.repository.create_run(run)
    return commands, task.task_id, run.run_id


def test_six_initial_gates_are_canonical_and_persist(tmp_path: Path) -> None:
    commands, task_id, run_id = _commands(tmp_path)
    gates = commands.list_gates(task_id, run_id)["items"]
    assert [gate["stage_id"] for gate in gates] == list(CANONICAL_STAGES)
    assert {gate["status"] for gate in gates} == {"not-ready"}
    assert FilesystemTaskRepository(tmp_path).get_gates(task_id, run_id)[0].trace_id == "trace-gate"


def test_gate_decision_is_idempotent_and_conflicts_do_not_overwrite(tmp_path: Path) -> None:
    commands, task_id, run_id = _commands(tmp_path)
    commands.mark_gate_waiting(task_id, run_id, CANONICAL_STAGES[0])
    artifact = FilesystemArtifactStore(commands.repository).commit_bytes(task_id, run_id, "planning.av-plan", "planning/av-plan.json", b"verified", CANONICAL_STAGES[0])
    evidence = [{"logical_key": artifact.artifact_key, "sha256": artifact.sha256}]
    first = commands.decide_gate(task_id, run_id, CANONICAL_STAGES[0], "approve", "reviewer", evidence=evidence)
    assert commands.decide_gate(task_id, run_id, CANONICAL_STAGES[0], "approve", "reviewer", evidence=evidence) == first
    with pytest.raises(DomainError, match="不能被静默覆盖"):
        commands.decide_gate(task_id, run_id, CANONICAL_STAGES[0], "redo", "reviewer", evidence=evidence)


def test_unapproved_upstream_blocks_before_execution_side_effects(tmp_path: Path) -> None:
    commands, task_id, run_id = _commands(tmp_path)
    with pytest.raises(DomainError) as error:
        commands.stage_run(task_id, run_id, "clone-voice", CommandContext(entrypoint=Entrypoint.CLI))
    assert error.value.code == "STAGE_GATE_REQUIRED"
    assert not (commands.repository.run_dir(task_id, run_id) / "gates.json").exists()
