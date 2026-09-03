"""Production behaviour coverage for CCB-TASK-CREATE-UPLOADED-PRESET-31."""
from __future__ import annotations
import hashlib
import io
import json
import threading
import pytest
from starlette.testclient import TestClient
from csboard.adapters.filesystem.repository import FilesystemTaskRepository
from csboard.application.commands import MountainCommands
from csboard.domain.models import Task
from webapp.mountain_server import create_app


def _submission(label="same"):
    return f"submit-{label}-{hashlib.sha256(label.encode()).hexdigest()[:24]}"


def _payload(label="task"):
    return {"title": f"任务 {label}", "summary": f"摘要 {label}", "engine": "whiteboard",
            "pipeline_id": "mountain-av-v1", "submission_id": _submission(label)}


def _form(**overrides):
    value = {"script": "这是用于六个标签页正式保存与恢复验证的一段完整测试文案。",
             "voice_source": "uploaded-reference", "visual_source": "preset", "style_asset_id": "ps-cs-1",
             "target_chars": "45", "shots_per_image": "2", "line_density": "rich", "brand_text": "CSBoard",
             "visual_anchor_enabled": "true", "include_subtitles": "true"}
    value.update(overrides)
    return value


def _create(client, label="task"):
    response = client.post("/api/v1/tasks", json=_payload(label))
    assert response.status_code == 200, response.text
    return response.json()


def _save(client, task_id, **overrides):
    return client.post(f"/api/v1/tasks/{task_id}/inputs", data=_form(**overrides),
                       files={"reference": ("voice.wav", io.BytesIO(b"RIFF" + b"x" * 128), "audio/wav")})


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(tmp_path))


def test_create_options_are_application_owned_and_exact(client, monkeypatch):
    expected = {"from": "application"}
    monkeypatch.setattr(MountainCommands, "create_options", lambda self: expected)
    assert client.get("/api/v1/tasks/create-options").json() == expected


def test_create_options_schema_defaults_and_unavailable_reason(client):
    body = client.get("/api/v1/tasks/create-options").json()
    assert body["defaults"] == {"engine": "whiteboard", "visual_source": "preset", "target_chars": 45,
                                "shots_per_image": 2, "line_density": "rich", "visual_anchor_enabled": True,
                                "include_subtitles": True}
    assert body["limits"] == {"script_min_chars": 10, "target_chars_min": 5,
                              "target_chars_max": 500, "brand_text_max_chars": 12}
    assert next(item for item in body["voice_sources"] if item["id"] == "voice-asset")["reason"] == "CAPABILITY_NOT_AVAILABLE"


def test_summary_round_trip_and_legacy_task_read(client):
    created = _create(client, "summary")
    assert client.get(f"/api/v1/tasks/{created['task_id']}").json()["task"]["summary"] == "摘要 summary"
    assert next(item for item in client.get("/api/v1/tasks").json()["items"] if item["task_id"] == created["task_id"])["summary"] == "摘要 summary"
    legacy = {"task_id": "legacy", "title": "旧任务", "pipeline_id": "mountain-av-v1", "engine": "whiteboard",
              "status": "ready", "created_at": "x", "updated_at": "x"}
    assert Task.from_dict(legacy).summary == "旧任务"


@pytest.mark.parametrize("payload", [
    {"title": "", "summary": "x", "submission_id": _submission("empty")},
    {"title": "x", "summary": "", "submission_id": _submission("nosummary")},
    {"title": "x", "summary": "x", "submission_id": "weak"},
    {"title": "x", "summary": "x", "submission_id": _submission("engine"), "engine": "infographic"},
])
def test_create_validates_formal_identity_fields(client, payload):
    response = client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 400 and response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_submission_is_sequentially_idempotent_and_conflicts(client):
    first = _create(client, "idempotent")
    second = client.post("/api/v1/tasks", json=_payload("idempotent")).json()
    assert (first["task_id"], first["run_id"], first["trace_id"]) == (second["task_id"], second["run_id"], second["trace_id"])
    conflict = _payload("idempotent"); conflict["summary"] = "changed"
    response = client.post("/api/v1/tasks", json=conflict)
    assert response.status_code == 409 and response.json()["error"]["code"] == "SUBMISSION_CONFLICT"


def test_submission_is_thread_safe_and_creates_one_task(tmp_path):
    app, barrier, responses = create_app(tmp_path), threading.Barrier(3), []
    def submit():
        with TestClient(app) as local:
            barrier.wait(); responses.append(local.post("/api/v1/tasks", json=_payload("parallel")).json())
    threads = [threading.Thread(target=submit) for _ in range(2)]
    [thread.start() for thread in threads]; barrier.wait(); [thread.join() for thread in threads]
    assert len({item["task_id"] for item in responses}) == 1
    assert len(list((tmp_path / "tasks").glob("*/task.json"))) == len(list((tmp_path / ".submissions").glob("*.json"))) == 1


class _SubmissionFaultRepository(FilesystemTaskRepository):
    def __init__(self, root, fail_at): super().__init__(root); self.fail_at = fail_at
    def _write_submission_checkpoint(self, name):
        if name == self.fail_at: raise OSError(name)


@pytest.mark.parametrize("checkpoint", ["before_task", "before_run", "before_index"])
def test_submission_failures_leave_no_partial_task_run_or_index(tmp_path, checkpoint):
    repo = _SubmissionFaultRepository(tmp_path, checkpoint)
    with pytest.raises(OSError): MountainCommands(tmp_path, repository=repo).create_task("x", summary="y", submission_id=_submission(checkpoint))
    assert not list((tmp_path / "tasks").glob("*/task.json")) and not list((tmp_path / ".submissions").glob("*.json"))


def test_uploaded_reference_preset_six_tab_round_trip_and_compatibility_mapping(client):
    created = _create(client, "six-tabs")
    assert _save(client, created["task_id"]).status_code == 200
    body = client.get(f"/api/v1/tasks/{created['task_id']}/inputs").json(); inputs = body["inputs"]
    assert {key: inputs[key] for key in ("script", "voice_source", "visual_source", "style_asset_id", "shots_per_image", "line_density", "brand_text", "pen_text", "stroke_detail")} == {
        "script": _form()["script"], "voice_source": "uploaded-reference", "visual_source": "preset", "style_asset_id": "ps-cs-1",
        "shots_per_image": 2, "line_density": "rich", "brand_text": "CSBoard", "pen_text": "CSBoard", "stroke_detail": "detailed"}
    assert body["rules"] == {"target_chars": 45, "min_chars": 27, "max_chars": 90}
    assert body["reference_audio"]["uploaded"] and inputs["style_snapshot"]["revision"] == 1
    assert str(client.app.state.data_dir) not in json.dumps(body, ensure_ascii=False)


@pytest.mark.parametrize("field,value", [("voice_source", "voice-asset"), ("visual_source", "custom-reference"),
    ("style_asset_id", "missing"), ("shots_per_image", "5"), ("line_density", "detailed"),
    ("brand_text", "x" * 13), ("target_chars", "4")])
def test_invalid_formal_fields_preserve_previously_committed_inputs(client, field, value):
    created = _create(client, f"invalid-{field}"); assert _save(client, created["task_id"]).status_code == 200
    task_dir = client.app.state.data_dir / "tasks" / created["task_id"]
    def digest(): return hashlib.sha256(b"".join(path.read_bytes() for path in (task_dir / "request.json", task_dir / "task.json", task_dir / "inputs" / "reference.wav"))).hexdigest()
    before = digest(); response = _save(client, created["task_id"], **{field: value})
    assert response.status_code == 400 and digest() == before


def test_create_then_failed_first_input_can_retry_without_second_task(client):
    created = _create(client, "retry")
    assert client.post(f"/api/v1/tasks/{created['task_id']}/inputs", data=_form()).status_code == 400
    assert client.post("/api/v1/tasks", json=_payload("retry")).json()["task_id"] == created["task_id"]
    assert _save(client, created["task_id"]).status_code == 200
    assert len(list((client.app.state.data_dir / "tasks").glob("*/task.json"))) == 1


def test_formal_save_does_not_persist_or_start_execution_strategy(client):
    created = _create(client, "no-start"); assert _save(client, created["task_id"]).status_code == 200
    request = json.loads((client.app.state.data_dir / "tasks" / created["task_id"] / "request.json").read_text())
    assert "execution_plan" not in request
    assert client.get(f"/api/v1/tasks/{created['task_id']}").json()["active_run"]["status"] == "pending"
