from __future__ import annotations
from pathlib import Path
from starlette.testclient import TestClient
from webapp.mountain_server import create_app

def _created(client: TestClient) -> tuple[str, str]:
    item = client.post("/api/v1/tasks", json={"title": "truth"}).json()
    return item["task_id"], item["run_id"]

def test_start_rejects_missing_reference_and_unsafe_reference(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path)); task_id, run_id = _created(client)
    assert client.post(f"/api/v1/tasks/{task_id}/inputs", data={"script": "这是足够长的输入文案但没有参考音频。"}).status_code == 200
    response = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start")
    assert response.status_code == 400 and "reference_audio" in response.json()["error"]["details"]["invalid_fields"]
    path = tmp_path / "tasks" / task_id / "request.json"
    import json
    data = json.loads(path.read_text()); data["reference_audio"] = "../../secret.wav"; path.write_text(json.dumps(data))
    assert client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start").status_code == 400
