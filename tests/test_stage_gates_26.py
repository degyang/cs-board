from __future__ import annotations
from pathlib import Path
from csboard.application.context import CommandContext
from csboard.domain.enums import Entrypoint
from tests.test_stage_gates_24 import _commands

def test_single_stage_gate_blocks_without_upstream_approval(tmp_path: Path) -> None:
    commands, task_id, run_id = _commands(tmp_path)
    try:
        commands.stage_run(task_id, run_id, "clone-voice", CommandContext(entrypoint=Entrypoint.CLI))
    except Exception as error:
        assert getattr(error, "code", None) == "STAGE_GATE_REQUIRED"
    else:
        raise AssertionError("unapproved upstream must block")
