from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_PATH = Path(__file__).parents[1] / "schemas/artifacts/generation-record.schema.json"


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _record(kind: str) -> dict:
    parameters = {
        "image": {"kind": "image", "width": 1024, "height": 1024, "format": "png", "steps": 30},
        "audio": {"kind": "audio", "sample_rate": 24000, "channels": 1, "format": "wav", "speed": 1.0},
        "video": {"kind": "video", "width": 1920, "height": 1080, "fps": 30, "container": "mp4", "codec": "h264"},
    }[kind]
    extension, mime_type = {"image": ("png", "image/png"), "audio": ("wav", "audio/wav"), "video": ("mp4", "video/mp4")}[kind]
    return {
        "schema_version": 1,
        "record_type": "asset-generation-record",
        "record_scope": "current",
        "asset_id": f"asset-{kind}-001",
        "asset_kind": kind,
        "identity": {"task_id": "task-001", "run_id": "run-001", "stage_id": "generate-assets", "unit_id": "unit-001", "visual_id": "visual-001"},
        "revision": 2,
        "parent_revision": 1,
        "is_current": True,
        "attempt": {"attempt_id": "attempt-002", "status": "succeeded", "started_at": "2026-09-06T10:00:00Z", "finished_at": "2026-09-06T10:01:00Z", "error_summary": None},
        "input_assets": [{"asset_id": "asset-source-001", "revision": 1, "sha256": "sha256:0123456789abcdef", "relative_path": "outputs/task-001/runs/run-001/assets/asset-source-001/current.png"}],
        "prompts": {"positive": "safe test prompt", "negative": None},
        "provider": {"service_id": "service-test", "provider_id": "provider-test", "model_id": "model-test", "public_parameters": {"quality": "standard"}},
        "generation_parameters": parameters,
        "random_seed": 42,
        "output": {"relative_path": f"outputs/task-001/runs/run-001/assets/asset-{kind}-001/current.{extension}", "mime_type": mime_type, "sha256": "sha256:abcdef0123456789", "size_bytes": 42},
        "created_at": "2026-09-06T10:01:00Z",
    }


@pytest.mark.parametrize("kind", ["image", "audio", "video"])
def test_current_generation_record_accepts_each_asset_kind(kind: str) -> None:
    record = _record(kind)
    assert not list(_validator().iter_errors(record))
    assert record["output"]["relative_path"].split("/")[1] == record["identity"]["task_id"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda record: record["output"].update(relative_path="/tmp/asset.png"),
        lambda record: record["output"].update(relative_path="outputs/task-001/../outside.png"),
        lambda record: record["provider"].update(api_key="redacted-test-value"),
        lambda record: record.pop("revision"),
        lambda record: record.update(record_scope="current", is_current=True, attempt={**record["attempt"], "status": "failed", "error_summary": {"code": "PROVIDER_FAILED", "message": "safe summary"}}, output=None),
    ],
    ids=["absolute-path", "path-traversal", "secret-field", "missing-revision", "failed-attempt-is-current"],
)
def test_generation_record_rejects_unsafe_or_invalid_state(mutation) -> None:
    record = copy.deepcopy(_record("image"))
    mutation(record)
    assert list(_validator().iter_errors(record))


def test_historical_failed_attempt_is_not_current_and_needs_no_output() -> None:
    record = _record("audio")
    record.update(
        record_scope="attempt",
        is_current=False,
        output=None,
        attempt={
            "attempt_id": "attempt-003",
            "status": "failed",
            "started_at": "2026-09-06T10:02:00Z",
            "finished_at": "2026-09-06T10:03:00Z",
            "error_summary": {"code": "PROVIDER_FAILED", "message": "safe summary"},
        },
    )
    assert not list(_validator().iter_errors(record))
