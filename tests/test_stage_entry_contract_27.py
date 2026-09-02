from __future__ import annotations
from pathlib import Path
from starlette.testclient import TestClient
from webapp.mountain_server import create_app

def test_start_has_not_found_invalid_input_and_waiting_boundaries(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    assert client.post("/api/v1/tasks/missing/runs/missing/start").status_code == 404
    created = client.post("/api/v1/tasks", json={"title": "entry contract"}).json()
    task_id, run_id = created["task_id"], created["run_id"]
    assert client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start").status_code == 400
    saved = client.post(f"/api/v1/tasks/{task_id}/inputs", data={"script": "这是足够长的持久化输入文案用于启动验证。", "style": "safe"}, files={"reference": ("voice.wav", b"RIFF-not-empty", "audio/wav")})
    assert saved.status_code == 200
    before = (tmp_path / "tasks" / task_id / "runs" / run_id / "run.json").read_bytes()
    response = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start")
    assert response.status_code == 200
    assert response.json()["state"] == "waiting-manual-trigger"
    assert (tmp_path / "tasks" / task_id / "runs" / run_id / "run.json").read_bytes() == before
