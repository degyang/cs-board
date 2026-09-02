"""Acceptance proof for execution-plan persistence and safety boundaries."""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from zipfile import ZipFile

import pytest
from starlette.testclient import TestClient

from csboard.adapters.filesystem.repository import FilesystemTaskRepository
from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.adapters.observability.jsonl import JsonlTelemetry
from csboard.adapters.secrets.secret_store import PlaintextSecretStore
from csboard.application.commands import MountainCommands
from csboard.application.service_resolver import ServiceResolver
from csboard.domain.errors import DomainError
from csboard.domain.enums import StageStatus
from csboard.domain.execution_plan import ExecutionPlan
from csboard.domain.models import StageState
from csboard.domain.service_definition import ServiceDefinition
from webapp.error_contract import domain_error_response
from webapp.mountain_server import create_app


SCRIPT_A = "这是用于执行计划验收的合成测试文案，内容足够长且不会调用任何外部能力。"
SCRIPT_B = "这是另一份用于事务并发验收的合成测试文案，内容同样足够长且完全隔离。"
PLAN_A = {"mode": "selective", "manual_stages": ["clone-voice"]}
PLAN_B = {"mode": "selective", "manual_stages": ["generate-illustrations", "compose-video"]}


def _snapshot(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}


def _task(client: TestClient, title: str = "执行计划验收任务") -> str:
    response = client.post("/api/v1/tasks", json={"title": title})
    assert response.status_code == 200
    return response.json()["task_id"]


def _save(client: TestClient, task_id: str, script: str = SCRIPT_A,
          plan: dict[str, object] = PLAN_A, reference: bytes | None = None,
          visual_anchor_enabled: bool = True) -> dict:
    response = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": script, "execution_mode": plan["mode"],
              "manual_stages": json.dumps(plan["manual_stages"]),
              "visual_anchor_enabled": str(visual_anchor_enabled).lower()},
        files={} if reference is None else {
            "reference": ("reference.wav", io.BytesIO(reference), "audio/wav")},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(("mode", "stages", "expected"), [
    ("auto", [], {"mode": "auto", "manual_stages": []}),
    ("selective", ["clone-voice"], {"mode": "selective", "manual_stages": ["clone-voice"]}),
    ("selective", ["compose-video", "generate-illustrations"],
     {"mode": "selective", "manual_stages": ["generate-illustrations", "compose-video"]}),
])
def test_execution_plan_valid_domain_matrix(mode: str, stages: list[str], expected: dict) -> None:
    assert ExecutionPlan.create(mode, stages).to_dict() == expected


def test_execution_plan_default_auto_domain_matrix() -> None:
    assert ExecutionPlan().to_dict() == {"mode": "auto", "manual_stages": []}
    assert ExecutionPlan.create().to_dict() == {"mode": "auto", "manual_stages": []}


@pytest.mark.parametrize(("mode", "stages"), [
    ("invalid", []), ("auto", ["clone-voice"]), ("selective", []),
    ("selective", ["unknown"]), ("selective", ["clone-voice", "clone-voice"]),
    ("selective", [""]), ("selective", [None]), ("selective", ["segment" + "-script"]),
])
def test_execution_plan_invalid_domain_matrix(mode: str, stages: list[object]) -> None:
    with pytest.raises(DomainError) as raised:
        ExecutionPlan.create(mode, stages)
    assert raised.value.code == "VALIDATION_ERROR"


@pytest.mark.parametrize(("mode", "manual_stages"), [
    ("invalid", "[]"), ("auto", '["clone-voice"]'), ("selective", "[]"),
    ("selective", '["unknown"]'), ("selective", '["clone-voice", "clone-voice"]'),
    ("selective", '[""]'), ("selective", "[null]"), ("selective", '["segment' + '-script"]'),
    ("auto", "not-json"), ("auto", "null"), ("auto", '"string"'), ("auto", "{}"), ("auto", "1"),
])
def test_execution_plan_invalid_api_matrix(tmp_path: Path, mode: str, manual_stages: str) -> None:
    client = TestClient(create_app(tmp_path))
    task_id = _task(client)
    response = client.post(f"/api/v1/tasks/{task_id}/inputs", data={
        "script": SCRIPT_A, "execution_mode": mode, "manual_stages": manual_stages})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_execution_plan_same_source_api_repository_and_cli_subprocess(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    task_id = _task(client)
    expected = {"mode": "selective", "manual_stages": ["generate-illustrations", "compose-video"]}
    posted = _save(client, task_id, plan=PLAN_B, visual_anchor_enabled=False)
    api_read = client.get(f"/api/v1/tasks/{task_id}/inputs").json()
    rebuilt = MountainCommands(tmp_path, repository=FilesystemTaskRepository(tmp_path)).get_inputs(task_id)
    completed = subprocess.run(
        [sys.executable, "-m", "cli.csboard", "--data-dir", str(tmp_path), "task", "show", "--task", task_id, "--json"],
        cwd=Path(__file__).parents[1], text=True, capture_output=True, check=True, timeout=30)
    assert posted["execution_plan"] == expected
    assert api_read["execution_plan"] == expected
    assert rebuilt["execution_plan"] == expected
    assert json.loads(completed.stdout)["execution_plan"] == expected
    expected_preparation = (FilesystemTaskRepository(tmp_path).read_json(
        tmp_path / "tasks" / task_id / "task.json")["script_preparation"])
    assert api_read["script_preparation"] == expected_preparation
    assert rebuilt["script_preparation"] == expected_preparation
    assert api_read["visual_anchor_enabled"] is False
    assert rebuilt["visual_anchor_enabled"] is False


def test_old_request_and_unsaved_inputs_default_auto_are_read_only(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    unsaved_task = _task(client, "未保存输入")
    unsaved_dir = tmp_path / "tasks" / unsaved_task
    before_unsaved = _snapshot(unsaved_dir)
    assert client.get(f"/api/v1/tasks/{unsaved_task}/inputs").json()["execution_plan"] == {"mode": "auto", "manual_stages": []}
    assert _snapshot(unsaved_dir) == before_unsaved

    old_task = _task(client, "旧 request")
    _save(client, old_task)
    repository = FilesystemTaskRepository(tmp_path)
    old_request = repository.get_request(old_task) or {}
    old_request.pop("execution_plan")
    repository.save_request(old_task, old_request)
    old_dir = tmp_path / "tasks" / old_task
    before_old_request = _snapshot(old_dir)
    assert client.get(f"/api/v1/tasks/{old_task}/inputs").json()["execution_plan"] == {"mode": "auto", "manual_stages": []}
    assert MountainCommands(tmp_path, repository=FilesystemTaskRepository(tmp_path)).show_task(old_task)["execution_plan"] == {"mode": "auto", "manual_stages": []}
    assert _snapshot(old_dir) == before_old_request


class _CheckpointRepository(FilesystemTaskRepository):
    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.checkpoint: str | None = None

    def _input_txn_checkpoint(self, name: str, context: dict) -> None:
        if name == self.checkpoint:
            raise OSError("injected checkpoint failure")


@pytest.mark.parametrize("checkpoint", [
    "request.after_backup", "request.after_install", "task.after_backup",
    "task.after_install", "reference.after_backup", "reference.after_install",
])
def test_checkpoint_failure_keeps_one_old_revision(tmp_path: Path, checkpoint: str) -> None:
    repository = _CheckpointRepository(tmp_path)
    client = TestClient(create_app(tmp_path, repository=repository))
    task_id = _task(client)
    _save(client, task_id, script=SCRIPT_A, plan=PLAN_A, reference=b"old-reference-bytes")
    task_dir = tmp_path / "tasks" / task_id
    old = _snapshot(task_dir)
    repository.checkpoint = checkpoint
    response = client.post(f"/api/v1/tasks/{task_id}/inputs", data={
        "script": SCRIPT_B, "execution_mode": "selective", "manual_stages": json.dumps(PLAN_B["manual_stages"])},
        files={"reference": ("reference.wav", io.BytesIO(b"new-reference-bytes"), "audio/wav")})
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert _snapshot(task_dir) == old, checkpoint


def test_concurrent_saves_leave_a_single_transaction_combination(tmp_path: Path) -> None:
    repository = FilesystemTaskRepository(tmp_path)
    app = create_app(tmp_path, repository=repository)
    task_id = _task(TestClient(app))
    barrier = threading.Barrier(2)
    results: list[int] = []

    def save(script: str, plan: dict[str, object], reference: bytes) -> None:
        barrier.wait(timeout=10)
        response = TestClient(app).post(f"/api/v1/tasks/{task_id}/inputs", data={
            "script": script, "execution_mode": plan["mode"], "manual_stages": json.dumps(plan["manual_stages"])},
            files={"reference": ("reference.wav", io.BytesIO(reference), "audio/wav")})
        results.append(response.status_code)

    left = threading.Thread(target=save, args=(SCRIPT_A, PLAN_A, b"reference-a"))
    right = threading.Thread(target=save, args=(SCRIPT_B, PLAN_B, b"reference-b"))
    left.start(); right.start(); left.join(timeout=30); right.join(timeout=30)
    assert not left.is_alive() and not right.is_alive()
    assert results == [200, 200]
    request = repository.get_request(task_id) or {}
    preparation = repository.read_json(repository.task_dir(task_id) / "task.json")["script_preparation"]
    selected = (request["script"], request["execution_plan"],
                (repository.task_dir(task_id) / "inputs" / "reference.wav").read_bytes())
    assert selected == (SCRIPT_A, PLAN_A, b"reference-a") or selected == (SCRIPT_B, PLAN_B, b"reference-b")
    assert "".join(unit["text"] for unit in preparation["voice_units"]) == request["script"]


class _UnavailableResolver:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def resolve(self, capability: str) -> object:
        self.calls.append(capability)
        raise DomainError("CAPABILITY_NOT_AVAILABLE", "isolated fake capability boundary")


def test_auto_start_is_fast_and_does_not_enter_pipeline(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    task_id = _task(client)
    _save(client, task_id, plan={"mode": "auto", "manual_stages": []})
    repository = FilesystemTaskRepository(tmp_path)
    resolver = _UnavailableResolver()
    commands = MountainCommands(tmp_path, repository=repository, service_resolver=resolver)
    run_id = repository.get_task(task_id).active_run_id or ""
    before = _snapshot(repository.task_dir(task_id))
    started = time.monotonic()
    result = commands.start_run(task_id, run_id)
    assert time.monotonic() - started < 30
    assert result["state"] == "waiting-manual-trigger"
    assert resolver.calls == []
    assert _snapshot(repository.task_dir(task_id)) == before


def test_selective_start_and_notfound_boundaries_are_side_effect_free(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    task_id = _task(client)
    plan = {"mode": "selective", "manual_stages": ["generate-visual-anchors"]}
    _save(client, task_id, plan=plan)
    task_dir = tmp_path / "tasks" / task_id
    run_id = FilesystemTaskRepository(tmp_path).get_task(task_id).active_run_id or ""
    before = _snapshot(task_dir)
    response = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start")
    assert response.status_code == 200
    assert response.json()["state"] == "waiting-manual-trigger"
    assert response.json()["next_stage"] == "generate-visual-anchors"
    assert "gates" in response.json()
    assert _snapshot(task_dir) == before
    assert client.post(f"/api/v1/tasks/{task_id}/runs/missing-run/start").status_code == 404
    other = _task(client, "另一个任务")
    assert client.post(f"/api/v1/tasks/{other}/runs/{run_id}/start").status_code == 404


def test_cli_subprocess_observes_the_same_immediate_manual_decision(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    task_id = _task(client)
    _save(client, task_id, plan={"mode": "selective", "manual_stages": ["generate-visual-anchors"]})
    run_id = FilesystemTaskRepository(tmp_path).get_task(task_id).active_run_id or ""
    completed = subprocess.run(
        [sys.executable, "-m", "cli.csboard", "--data-dir", str(tmp_path), "pipeline", "run",
         "--task", task_id, "--run", run_id, "--json"],
        cwd=Path(__file__).parents[1], text=True, capture_output=True, check=True, timeout=30)
    decision = json.loads(completed.stdout)
    assert decision["state"] == "waiting-manual-trigger"
    assert decision["next_stage"] == "generate-visual-anchors"


def test_concurrent_pipeline_calls_do_not_duplicate_automatic_prefix(tmp_path: Path) -> None:
    commands = MountainCommands(tmp_path, repository=FilesystemTaskRepository(tmp_path))
    created = commands.create_task("并发执行计划")
    task_id, run_id = created["task_id"], created["run_id"]
    repository = commands.repository
    repository.save_request(task_id, {"execution_plan": {
        "mode": "selective", "manual_stages": ["clone-voice"]}})
    calls: list[str] = []

    def anchor_executor(executor_task: str, executor_run: str, context: object) -> dict:
        calls.append(executor_run)
        run = repository.get_run(executor_task, executor_run)
        run.stages["generate-visual-anchors"] = StageState(StageStatus.SUCCEEDED, 1)
        repository.save_run(run)
        return {"ok": True, "stage": "generate-visual-anchors"}

    commands.pipeline.register_stage("generate-visual-anchors", anchor_executor)
    barrier = threading.Barrier(2)
    decisions: list[dict] = []

    def run_pipeline() -> None:
        barrier.wait(timeout=10)
        decisions.append(commands.pipeline_run(task_id, run_id))

    left = threading.Thread(target=run_pipeline)
    right = threading.Thread(target=run_pipeline)
    left.start(); right.start(); left.join(timeout=30); right.join(timeout=30)
    assert not left.is_alive() and not right.is_alive()
    assert calls == [run_id]
    assert all(item["state"] == "waiting-manual-trigger" for item in decisions)
    assert all(item["next_stage"] == "clone-voice" for item in decisions)


def test_api_cli_event_log_and_diagnostic_are_redacted(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    task_id = _task(client)
    secret = "TOP_SECRET_SHOULD_NOT_ESCAPE"
    script = f"合成测试脚本 {secret}，长度足够用于持久化和脱敏验证。"
    reference = b"REFERENCE_BYTES_SHOULD_NOT_ESCAPE"
    _save(client, task_id, script=script, plan=PLAN_A, reference=reference)
    repository = FilesystemTaskRepository(tmp_path)
    run_id = repository.get_task(task_id).active_run_id or ""
    telemetry = JsonlTelemetry(repository)
    telemetry.append_event(task_id, run_id, {"script": script, "secret": secret, "absolute_path": str(tmp_path)})
    telemetry.append_log(task_id, run_id, {"reference_bytes": reference.decode(), "secret": secret, "absolute_path": str(tmp_path)})
    outputs = [client.get(f"/api/v1/tasks/{task_id}").text,
               client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start").text,
               client.get(f"/api/v1/tasks/{task_id}/runs/{run_id}/events").text,
               client.get(f"/api/v1/tasks/{task_id}/runs/{run_id}/logs").text,
               subprocess.run([sys.executable, "-m", "cli.csboard", "--data-dir", str(tmp_path), "task", "show", "--task", task_id, "--json"],
                              cwd=Path(__file__).parents[1], text=True, capture_output=True, check=True, timeout=30).stdout]
    diagnostic = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/diagnostics").json()
    with ZipFile(io.BytesIO(client.get(diagnostic["download_url"]).content)) as bundle:
        outputs.append("\n".join(bundle.read(name).decode("utf-8") for name in bundle.namelist()))
    combined = "\n".join(outputs)
    for value in (script, secret, reference.decode(), str(tmp_path), "Traceback"):
        assert value not in combined


def test_domain_error_response_details_precedence_and_fallback() -> None:
    fallback = domain_error_response(DomainError("X", "safe", details={"fallback": True})).body
    explicit = domain_error_response(DomainError("X", "safe", details={"fallback": True}), details={"explicit": True}).body
    assert json.loads(fallback)["error"]["details"] == {"fallback": True}
    assert json.loads(explicit)["error"]["details"] == {"explicit": True}


def _service(service_id: str, **kwargs: object) -> ServiceDefinition:
    values: dict[str, object] = {"service_id": service_id, "display_name": service_id,
        "capability": "text_generation", "adapter_type": "openai_compatible", "endpoint": "https://example.invalid",
        "model": "test", "enabled": True, "priority": 100, "is_default": False, "config": {},
        "required_secrets": [], "optional_secrets": []}
    values.update(kwargs)
    return ServiceDefinition(**values)


def test_service_resolver_required_optional_default_and_priority_matrix(tmp_path: Path) -> None:
    secrets = PlaintextSecretStore(tmp_path / "secrets.json")
    registry = FilesystemServiceRegistry(tmp_path, secrets)
    resolver = ServiceResolver(registry)
    registry.create_service(_service("no-required"))
    assert resolver.resolve("text_generation").service_id == "no-required"
    registry.create_service(_service("required", required_secrets=["one", "two"], priority=1))
    assert resolver.resolve("text_generation").service_id == "no-required"
    secrets.set("required_one", "one"); secrets.set("required_two", "two")
    registry.set_default("required")
    assert resolver.resolve("text_generation").service_id == "required"
    registry.create_service(_service("optional", optional_secrets=["not-set"], priority=0))
    registry.set_default("optional")
    assert resolver.resolve("text_generation").service_id == "optional"
    registry.create_service(_service("missing-default", required_secrets=["missing"], is_default=True, priority=0))
    assert resolver.resolve_configured("text_generation").service_id == "missing-default"
    assert resolver.resolve("text_generation").service_id == "optional"


def test_secret_store_exception_fails_closed_without_leaking(tmp_path: Path) -> None:
    class ExplodingStore:
        def get(self, key: str) -> str | None:
            raise RuntimeError("SECRET_STORE_INTERNAL_TEXT")
    registry = FilesystemServiceRegistry(tmp_path, ExplodingStore())
    registry.create_service(_service("broken", required_secrets=["api_key"]))
    with pytest.raises(DomainError) as raised:
        ServiceResolver(registry).resolve("text_generation")
    assert "SECRET_STORE_INTERNAL_TEXT" not in str(raised.value)
