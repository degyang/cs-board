from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from csboard.domain.execution_plan import ExecutionPlan
from csboard.domain.errors import DomainError
from webapp.mountain_server import create_app


def test_execution_plan_normalizes_and_validates() -> None:
    assert ExecutionPlan.create("selective", ["compose-video", "generate-illustrations"]).to_dict() == {
        "mode": "selective",
        "manual_stages": ["generate-illustrations", "compose-video"],
    }
    for mode, stages in (("auto", ["clone-voice"]), ("selective", [])):
        try:
            ExecutionPlan.create(mode, stages)
        except DomainError as exc:
            assert exc.code == "VALIDATION_ERROR"
        else:
            raise AssertionError("invalid execution plan accepted")


def test_api_readback_and_selective_start_are_side_effect_free(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    task_id = client.post("/api/v1/tasks", json={"title": "合成测试 Task（测试数据）"}).json()["task_id"]
    saved = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={
            "script": "这是明确标记为合成测试输入的文案内容。",
            "execution_mode": "selective",
            "manual_stages": '["compose-video", "generate-illustrations"]',
        },
    )
    assert saved.status_code == 200
    assert client.get(f"/api/v1/tasks/{task_id}/inputs").json()["execution_plan"] == {
        "mode": "selective",
        "manual_stages": ["generate-illustrations", "compose-video"],
    }
    run_id = client.get(f"/api/v1/tasks/{task_id}").json()["active_run"]["run_id"]
    before = (tmp_path / "tasks" / task_id / "runs" / run_id / "run.json").read_bytes()
    response = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EXECUTION_PLAN_NOT_READY"
    assert (tmp_path / "tasks" / task_id / "runs" / run_id / "run.json").read_bytes() == before


def test_invalid_manual_stages_json_is_400(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    task_id = client.post("/api/v1/tasks", json={"title": "合成测试 Task（测试数据）"}).json()["task_id"]
    response = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是明确标记为合成测试输入的文案内容。", "manual_stages": "not-json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
