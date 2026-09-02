from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from starlette.testclient import TestClient

from csboard.adapters.filesystem import FilesystemArtifactStore, FilesystemTaskRepository
from csboard.application.commands import MountainCommands
from csboard.domain.errors import DomainError
from csboard.domain.execution_plan import CANONICAL_STAGES
from csboard.domain.work_order import STAGE_SKILLS, StageWorkOrder
from webapp.mountain_server import create_app


SCRIPT = "这是用于工作单持久化和安全投影的测试文案，长度足够且不应出现在工作单响应中。"


def _created(tmp_path: Path) -> tuple[TestClient, str, str]:
    client = TestClient(create_app(tmp_path))
    created = client.post("/api/v1/tasks", json={"title": "工作单测试"}).json()
    task_id, run_id = created["task_id"], created["run_id"]
    response = client.post(f"/api/v1/tasks/{task_id}/inputs", data={
        "script": SCRIPT, "execution_mode": "selective",
        "manual_stages": json.dumps(["clone-voice", "compose-video"]),
        "style": "safe-style",
    })
    assert response.status_code == 200, response.text
    return client, task_id, run_id


def test_every_stage_has_stable_schema_valid_persisted_work_order(tmp_path: Path) -> None:
    client, task_id, run_id = _created(tmp_path)
    schema = json.loads((Path(__file__).parents[1] / "schemas/mountain/stage-work-order.schema.json").read_text())
    validator = Draft202012Validator(schema)
    for stage in CANONICAL_STAGES:
        first = client.get(f"/api/v1/tasks/{task_id}/runs/{run_id}/work-orders/{stage}")
        second = client.get(f"/api/v1/tasks/{task_id}/runs/{run_id}/work-orders/{stage}")
        assert first.status_code == second.status_code == 200
        document = first.json()
        assert document["work_order_id"] == second.json()["work_order_id"]
        assert document["input_fingerprint"] == second.json()["input_fingerprint"]
        assert document["identity"]["skill"] == STAGE_SKILLS[stage]
        assert document["status"] == ("waiting-manual-trigger" if stage in {"clone-voice", "compose-video"} else "ready")
        assert not list(validator.iter_errors(document))
        path = tmp_path / "tasks" / task_id / "runs" / run_id / "work-orders" / stage / "work-order.json"
        assert path.is_file()


def test_upstream_artifact_change_creates_new_revision_and_stales_old_audit(tmp_path: Path) -> None:
    client, task_id, run_id = _created(tmp_path)
    endpoint = f"/api/v1/tasks/{task_id}/runs/{run_id}/work-orders/clone-voice"
    first = client.get(endpoint).json()
    store = FilesystemArtifactStore(FilesystemTaskRepository(tmp_path))
    store.commit_bytes(task_id, run_id, "planning.av-plan", "planning/av-plan.json", b"one", "generate-visual-anchors")
    second = client.get(endpoint).json()
    assert second["revision"] == 2
    assert second["work_order_id"] != first["work_order_id"]
    old = json.loads((tmp_path / "tasks" / task_id / "runs" / run_id / "work-orders" / "clone-voice" / "revisions" / "1" / "work-order.json").read_text())
    assert old["status"] == "stale"
    assert second["input_artifacts"][0]["artifact_key"] == "planning.av-plan"


def test_api_and_cli_show_the_same_safe_fact(tmp_path: Path) -> None:
    client, task_id, run_id = _created(tmp_path)
    api = client.get(f"/api/v1/tasks/{task_id}/runs/{run_id}/work-orders/clone-voice").json()
    completed = subprocess.run(
        [sys.executable, "-m", "cli.csboard", "--data-dir", str(tmp_path), "work-order", "show",
         "--task", task_id, "--run", run_id, "--stage", "clone-voice", "--json"],
        cwd=Path(__file__).parents[1], text=True, capture_output=True, check=True, timeout=30)
    cli = json.loads(completed.stdout)
    assert cli == api
    exposed = completed.stdout + json.dumps(api, ensure_ascii=False)
    assert SCRIPT not in exposed
    assert str(tmp_path) not in exposed
    assert "api_key" not in exposed.lower()


def test_domain_rejects_escape_paths_and_invalid_state_transitions() -> None:
    common = {
        "schema_version": "1.0", "work_order_id": "wo-test", "identity": {
            "task_id": "task-1", "run_id": "run-1", "stage": "clone-voice", "skill": "voice-cloner",
            "pipeline_id": "mountain-av-v1", "engine": "whiteboard"}, "revision": 1,
        "input_fingerprint": "sha256:" + "0" * 64, "status": "ready", "scope": {"kind": "stage"},
        "input_artifacts": [], "parameters_path": "work-orders/clone-voice/parameters.json",
        "instructions_path": "work-orders/clone-voice/instructions.md", "output_directory": "work-orders/clone-voice/output",
        "expected_outputs": [], "commands": {name: [] for name in ("run", "import", "validate", "accept", "reject", "retry")},
        "next_action": {"code": "CAPABILITY_NOT_AVAILABLE", "message": "not implemented"},
    }
    order = StageWorkOrder(**common)
    assert order.transition("waiting-manual-trigger").status == "waiting-manual-trigger"
    with pytest.raises(DomainError):
        order.transition("succeeded")
    with pytest.raises(DomainError):
        StageWorkOrder(**{**common, "parameters_path": "/tmp/escape.json"})
