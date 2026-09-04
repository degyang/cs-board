from __future__ import annotations

import hashlib
import json

import pytest
from starlette.testclient import TestClient

from csboard.adapters.filesystem.repository import FilesystemTaskRepository
from csboard.application.commands import MountainCommands
from csboard.domain.errors import DomainError
from webapp.mountain_server import create_app


def _submission(label: str) -> str:
    return f"package-{label}-{hashlib.sha256(label.encode()).hexdigest()[:24]}"


def _payload(label: str, **extra: object) -> dict[str, object]:
    return {
        "title": f"任务 {label}", "summary": "任务包测试", "engine": "whiteboard",
        "pipeline_id": "mountain-av-v1", "submission_id": _submission(label), **extra,
    }


@pytest.fixture()
def package_env(tmp_path):
    project = tmp_path / "project"; project.mkdir()
    state = tmp_path / "state"; state.mkdir()
    repository = FilesystemTaskRepository(state, project_root=project)
    return project, state, repository


def test_api_default_root_creates_complete_canonical_package(package_env):
    project, state, repository = package_env
    client = TestClient(create_app(state, repository=repository))
    response = client.post("/api/v1/tasks", json=_payload("default"))
    assert response.status_code == 200, response.text
    task_id, run_id = response.json()["task_id"], response.json()["run_id"]
    package = project / "outputs" / task_id
    assert repository.task_dir(task_id) == package
    assert not (state / "tasks" / task_id).exists()
    assert {"task.json", "task-package.json", "inputs", "runs"} <= {item.name for item in package.iterdir()}
    assert {"assets", "parameters"} <= {item.name for item in (package / "inputs").iterdir()}
    assert {"planning", "audio", "images", "clips", "subtitles", "manifests", "evidence", "final"} <= {item.name for item in (package / "runs" / run_id).iterdir()}
    index = json.loads((package / "task-package.json").read_text())
    assert index["task_id"] == task_id and index["runs_dir"] == "runs"
    assert client.get("/api/v1/tasks").json()["items"][0]["task_id"] == task_id


def test_custom_root_isolated_and_outside_project_is_rejected(package_env):
    project, state, repository = package_env
    commands = MountainCommands(state, repository=repository)
    first = commands.create_task("first", summary="a", submission_id=_submission("first"), request={"output_root": "exports"})
    second = commands.create_task("second", summary="b", submission_id=_submission("second"), request={"output_root": "exports"})
    assert repository.task_dir(first["task_id"]) == project / "exports" / first["task_id"]
    assert repository.run_dir(first["task_id"], first["run_id"]) != repository.run_dir(second["task_id"], second["run_id"])
    with pytest.raises(DomainError, match="项目目录"):
        commands.create_task("outside", summary="c", submission_id=_submission("outside"), request={"output_root": str(project.parent / "outside")})
    assert not list((project.parent / "outside").glob("task-*")) if (project.parent / "outside").exists() else True
    client = TestClient(create_app(state, repository=repository))
    response = client.post("/api/v1/tasks", json=_payload("api-outside", output_root=str(project.parent / "outside")))
    assert response.status_code == 400 and response.json()["error"]["code"] == "OUTPUT_ROOT_FORBIDDEN"


class _FaultyPackageRepository(FilesystemTaskRepository):
    def _package_txn_checkpoint(self, name: str, task_id: str) -> None:
        if name == "before_locator":
            raise OSError("simulated locator failure")


def test_package_creation_failure_rolls_back_without_legacy_fallback(tmp_path):
    project = tmp_path / "project"; project.mkdir()
    state = tmp_path / "state"; state.mkdir()
    repository = _FaultyPackageRepository(state, project_root=project)
    commands = MountainCommands(state, repository=repository)
    with pytest.raises(OSError, match="simulated"):
        commands.create_task("broken", summary="b", submission_id=_submission("broken"))
    assert not list((project / "outputs").glob("task-*"))
    assert not list((state / ".task-packages").glob("*.json"))
    assert not list((state / "tasks").glob("*/task.json")) if (state / "tasks").exists() else True
