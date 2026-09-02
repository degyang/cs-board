from __future__ import annotations
from pathlib import Path
import hashlib
import json
import pytest
from starlette.testclient import TestClient
from webapp.mountain_server import create_app
from csboard.adapters.filesystem import FilesystemArtifactStore
from csboard.domain.execution_plan import CANONICAL_STAGES
from tests.test_stage_gates_24 import _commands

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

def _snapshot(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}

@pytest.mark.parametrize("mutate,field", [
    (lambda value: value.pop("script"), "script"),
    (lambda value: value.__setitem__("script", "short"), "script"),
    (lambda value: value.__setitem__("reference_audio", "inputs/missing.wav"), "reference_audio"),
    (lambda value: value.__setitem__("reference_audio", "/tmp/audio.wav"), "reference_audio"),
])
def test_start_input_matrix_has_no_task_tree_side_effects(tmp_path: Path, mutate, field: str) -> None:
    client = TestClient(create_app(tmp_path)); task_id, run_id = _created(client)
    assert client.post(f"/api/v1/tasks/{task_id}/inputs", data={"script": "这是足够长的输入文案并保存真实参考音频。"}, files={"reference": ("voice.wav", b"RIFF-audio", "audio/wav")}).status_code == 200
    root = tmp_path / "tasks" / task_id; request = root / "request.json"; value = json.loads(request.read_text()); mutate(value); request.write_text(json.dumps(value))
    before = _snapshot(root); response = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start")
    assert response.status_code == 400 and response.json()["error"]["details"]["invalid_fields"] == [field]
    assert _snapshot(root) == before and str(tmp_path) not in response.text

def _output(commands, task_id: str, run_id: str, stage: str) -> None:
    from csboard.application.work_orders import STAGE_OUTPUTS
    store = FilesystemArtifactStore(commands.repository)
    for key in STAGE_OUTPUTS[stage]: store.commit_bytes(task_id, run_id, key, f"safe/{key}.json", key.encode(), stage)

@pytest.mark.parametrize("stage,state", [("generate-visual-anchors", "succeeded"), ("generate-visual-anchors", "skipped"), ("compose-video", "succeeded")])
def test_valid_outputs_require_review_even_final_stage(tmp_path: Path, stage: str, state: str) -> None:
    commands, task_id, run_id = _commands(tmp_path); _output(commands, task_id, run_id, stage)
    response = commands._stage_response(task_id, run_id, stage, {"ok": True, "result": state, "task_id": task_id, "run_id": run_id, "trace_id": "trace-gate", "stage": stage})
    assert response["ok"] and response["next_action"]["code"] == "GATE_REVIEW_REQUIRED"
    assert commands.get_gate(task_id, run_id, stage)["status"] == "waiting-review"
    if stage == "compose-video": assert response["next_stage"] is None

def test_invalid_output_failed_identity_and_gate_write_failure_are_safe(tmp_path: Path, monkeypatch) -> None:
    commands, task_id, run_id = _commands(tmp_path)
    bad = commands._stage_response(task_id, run_id, "generate-visual-anchors", {"ok": True, "result": "succeeded"})
    assert not bad["ok"] and bad["next_action"]["code"] == "STAGE_OUTPUT_INVALID" and bad["next_stage"] is None
    failed = commands._stage_response(task_id, run_id, "generate-visual-anchors", {"ok": False, "result": "failed"})
    assert not failed["ok"] and failed["stages_executed"] == ["generate-visual-anchors"] and failed["next_action"]["code"] == "FIX_STAGE_RESULT"
    conflict = commands._stage_response(task_id, run_id, "generate-visual-anchors", {"ok": True, "result": "succeeded", "task_id": "evil"})
    assert conflict["results"][0]["task_id"] == task_id and conflict["results"][0]["error"] == "STAGE_RESPONSE_IDENTITY_CONFLICT"
    _output(commands, task_id, run_id, "generate-visual-anchors")
    monkeypatch.setattr(type(commands), "mark_gate_waiting", lambda *_: (_ for _ in ()).throw(OSError("disk")))
    persisted = commands._stage_response(task_id, run_id, "generate-visual-anchors", {"ok": True, "result": "succeeded"})
    assert not persisted["ok"] and persisted["next_action"]["code"] == "STAGE_GATE_PERSIST_FAILED"
