from __future__ import annotations

import copy
import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from csboard.adapters.filesystem import FilesystemGenerationRecordStore, FilesystemTaskRepository
from csboard.domain.enums import Engine, Entrypoint, RunStatus, TaskStatus
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.models import Run, Task
from backend.mountain_task_api import mountain_task_router


def _repository(tmp_path: Path) -> tuple[FilesystemTaskRepository, str, str]:
    repository = FilesystemTaskRepository(tmp_path)
    task_id, run_id = "task-001", "run-001"
    repository.create_task(Task(task_id, "Asset record", "mountain-av-v1", Engine.WHITEBOARD,
                                TaskStatus.READY, "2026-09-06T10:00:00Z", "2026-09-06T10:00:00Z",
                                summary="Asset record", active_run_id=run_id))
    repository.create_run(Run(run_id, task_id, "trace-001", Entrypoint.WEB, ["cmd-001"],
                              RunStatus.PENDING, "compose-video", "2026-09-06T10:00:00Z"))
    return repository, task_id, run_id


def _record(kind: str = "image", *, scope: str = "current") -> dict:
    params = {
        "image": {"kind": "image", "width": 2, "height": 2, "format": "png"},
        "audio": {"kind": "audio", "sample_rate": 24000, "channels": 1, "format": "wav"},
        "video": {"kind": "video", "width": 2, "height": 2, "fps": 24, "container": "mp4", "codec": "h264"},
    }[kind]
    extension, mime = {"image": ("png", "image/png"), "audio": ("wav", "audio/wav"), "video": ("mp4", "video/mp4")}[kind]
    current = scope == "current"
    return {
        "schema_version": 1, "record_type": "asset-generation-record", "record_scope": scope,
        "asset_id": f"asset-{kind}-001", "asset_kind": kind,
        "identity": {"task_id": "task-001", "run_id": "run-001", "stage_id": "generate-assets", "unit_id": "unit-001", "visual_id": "visual-001"},
        "revision": 1, "parent_revision": None, "is_current": current,
        "attempt": {"attempt_id": "attempt-001", "status": "succeeded" if current else "failed", "started_at": "2026-09-06T10:00:00Z", "finished_at": "2026-09-06T10:01:00Z", "error_summary": None if current else {"code": "SAFE_FAILURE", "message": "safe summary"}},
        "input_assets": [], "prompts": {"positive": "safe prompt", "negative": None},
        "provider": {"service_id": "service-test", "provider_id": "provider-test", "model_id": "model-test", "public_parameters": {}},
        "generation_parameters": params, "random_seed": 1,
        "output": {"relative_path": f"outputs/task-001/runs/run-001/assets/asset-{kind}-001/current.{extension}", "mime_type": mime, "sha256": "sha256:0123456789abcdef", "size_bytes": 4} if current else None,
        "created_at": "2026-09-06T10:01:00Z",
    }


@pytest.mark.parametrize("kind", ["image", "audio", "video"])
def test_current_records_for_each_kind_round_trip(tmp_path: Path, kind: str) -> None:
    repository, task_id, run_id = _repository(tmp_path)
    store = FilesystemGenerationRecordStore(repository)
    record = _record(kind)
    store.save_current(task_id, run_id, record["asset_id"], record)
    assert store.read_current(task_id, run_id, record["asset_id"]) == record
    assert (repository.run_dir(task_id, run_id) / "assets" / record["asset_id"] / "generation.json").is_file()


def test_historical_attempt_does_not_replace_current(tmp_path: Path) -> None:
    repository, task_id, run_id = _repository(tmp_path)
    store = FilesystemGenerationRecordStore(repository)
    current, attempt = _record(), _record(scope="attempt")
    store.save_current(task_id, run_id, current["asset_id"], current)
    store.save_attempt(task_id, run_id, attempt["asset_id"], attempt)
    assert store.read_current(task_id, run_id, current["asset_id"]) == current
    assert (repository.run_dir(task_id, run_id) / "assets" / attempt["asset_id"] / "attempts" / "attempt-001.json").is_file()


@pytest.mark.parametrize("mutation", [
    lambda value: value["output"].update(relative_path="outputs/task-001/../outside.png"),
    lambda value: value["identity"].update(task_id="other-task"),
    lambda value: value.update(asset_id="other-asset"),
    lambda value: value["provider"].update(authorization="redacted-test-value"),
    lambda value: value.pop("revision"),
], ids=["path-escape", "task-mismatch", "asset-mismatch", "secret-field", "invalid-schema"])
def test_invalid_write_preserves_existing_current(tmp_path: Path, mutation) -> None:
    repository, task_id, run_id = _repository(tmp_path)
    store = FilesystemGenerationRecordStore(repository)
    current = _record()
    store.save_current(task_id, run_id, current["asset_id"], current)
    path = repository.run_dir(task_id, run_id) / "assets" / current["asset_id"] / "generation.json"
    before = path.read_bytes()
    invalid = copy.deepcopy(current)
    mutation(invalid)
    with pytest.raises(DomainError):
        store.save_current(task_id, run_id, current["asset_id"], invalid)
    assert path.read_bytes() == before
    assert not list(path.parent.glob("*.tmp"))


def test_missing_record_and_route_escape_are_safe(tmp_path: Path) -> None:
    repository, task_id, run_id = _repository(tmp_path)
    store = FilesystemGenerationRecordStore(repository)
    with pytest.raises(NotFoundError):
        store.read_current(task_id, run_id, "asset-missing")
    with pytest.raises(DomainError):
        store.read_current(task_id, run_id, "../asset")


def _app(tmp_path: Path, repository: FilesystemTaskRepository) -> FastAPI:
    app = FastAPI()
    app.include_router(mountain_task_router(tmp_path, repository=repository))
    return app


def _get(app: FastAPI, path: str) -> httpx.Response:
    """Make an in-process ASGI HTTP request without the TestClient portal."""
    async def request() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver",
        ) as client:
            return await client.get(path)
    return asyncio.run(request())


def test_generation_endpoint_uses_asgi_http_without_path_leak(tmp_path: Path) -> None:
    repository, task_id, run_id = _repository(tmp_path)
    store = FilesystemGenerationRecordStore(repository)
    record = _record()
    media_path = tmp_path / record["output"]["relative_path"]
    media_path.parent.mkdir(parents=True, exist_ok=True)
    media_path.write_bytes(b"safe")
    store.save_current(task_id, run_id, record["asset_id"], record)
    app = _app(tmp_path, repository)
    base = f"/api/v1/tasks/{task_id}/runs/{run_id}/assets/{record['asset_id']}"
    generation = _get(app, f"{base}/generation")
    missing = _get(app, f"/api/v1/tasks/{task_id}/runs/{run_id}/assets/asset-missing/generation")
    assert generation.status_code == 200 and generation.json() == record
    assert missing.status_code == 404
    assert str(tmp_path) not in missing.text
    assert missing.json()["error"]["code"] == "NOT_FOUND"

    router = next(route for route in app.routes if getattr(route, "path", "").endswith("/assets/{asset_id}/media"))
    media = asyncio.run(router.endpoint(task_id, run_id, record["asset_id"]))
    assert media.status_code == 200 and media.headers["content-type"].startswith("image/png")
    assert media.path.read_bytes() == b"safe"


def test_list_current_assets_via_asgi_http_is_stable_and_complete(tmp_path: Path) -> None:
    repository, task_id, run_id = _repository(tmp_path)
    store = FilesystemGenerationRecordStore(repository)
    records = [_record("video"), _record("image"), _record("audio")]
    for record in records:
        store.save_current(task_id, run_id, record["asset_id"], record)
    assets_dir = repository.run_dir(task_id, run_id) / "assets"
    (assets_dir / "not-an-asset").mkdir()
    (assets_dir / "not-a-directory").write_text("ignore", encoding="utf-8")

    response = _get(_app(tmp_path, repository), f"/api/v1/tasks/{task_id}/runs/{run_id}/assets")
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["asset_id"] for item in items] == ["asset-audio-001", "asset-image-001", "asset-video-001"]
    assert [item["asset_kind"] for item in items] == ["audio", "image", "video"]
    assert [item["generation_record"] for item in items] == sorted(records, key=lambda record: record["asset_id"])
    assert [item["media_url"] for item in items] == [
        f"/api/v1/tasks/{task_id}/runs/{run_id}/assets/{asset_id}/media"
        for asset_id in ("asset-audio-001", "asset-image-001", "asset-video-001")
    ]


def test_list_current_assets_empty_and_safe_failures_via_asgi_http(tmp_path: Path) -> None:
    repository, task_id, run_id = _repository(tmp_path)
    app = _app(tmp_path, repository)
    base = f"/api/v1/tasks/{task_id}/runs/{run_id}/assets"
    assert _get(app, base).json() == {"items": []}

    invalid_path = repository.run_dir(task_id, run_id) / "assets" / "asset-corrupt"
    invalid_path.mkdir(parents=True)
    invalid_path.joinpath("generation.json").write_text("{not json", encoding="utf-8")
    corrupt = _get(app, base)
    assert corrupt.status_code == 400
    assert corrupt.json()["error"]["code"] == "GENERATION_RECORD_INVALID"

    invalid_path.joinpath("generation.json").unlink()
    mismatched = _record()
    mismatched["asset_id"] = "other-asset"
    invalid_path.joinpath("generation.json").write_text(json.dumps(mismatched), encoding="utf-8")
    identity = _get(app, base)
    assert identity.status_code == 400
    assert identity.json()["error"]["code"] == "GENERATION_RECORD_IDENTITY_MISMATCH"

    for url in ("/api/v1/tasks/no-task/runs/no-run/assets", f"/api/v1/tasks/{task_id}/runs/no-run/assets", f"/api/v1/tasks/{task_id}/runs/%2E%2E/assets"):
        response = _get(app, url)
        assert response.status_code in {400, 404}
        assert str(tmp_path) not in response.text
