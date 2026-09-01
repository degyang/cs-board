from __future__ import annotations

import hashlib
import json
from typing import Any

from csboard.application.context import new_id, utc_now
from csboard.domain.av_timing import UnitTiming, VoiceUnit
from csboard.domain.enums import Engine


def av_plan_document(task_id: str, run_id: str, units: tuple[VoiceUnit, ...], source_text: str, engine: Engine = Engine.WHITEBOARD) -> dict[str, Any]:
    return {
        **_metadata("av-plan", "planning.av-plan", task_id, run_id, "generate-visual-anchors", engine),
        "source_text_sha256": _sha(source_text),
        "voice_units": [{
            "unit_id": unit.unit_id, "order": unit.order, "source_range": _range(unit.source_range), "text": unit.text,
            "visual_items": [{"visual_id": item.visual_id, "order": item.order, "source_range": _range(item.source_range), "text": item.text} for item in unit.visual_items],
        } for unit in units],
    }


def timeline_document(task_id: str, run_id: str, timings: tuple[UnitTiming, ...], engine: Engine = Engine.WHITEBOARD) -> dict[str, Any]:
    return {
        **_metadata("timeline", "timing.timeline", task_id, run_id, "clone-voice", engine),
        "units": [{
            "unit_id": item.unit_id, "duration_ms": item.duration_ms, "timing_source": item.timing_source.value,
            "alignment": item.alignment,
            "visual_timings": [{"visual_id": visual.visual_id, "start_ms": visual.start_ms, "end_ms": visual.end_ms} for visual in item.visual_timings],
        } for item in timings],
    }


def voice_manifest_document(task_id: str, run_id: str, voices: list[dict[str, Any]], engine: Engine = Engine.WHITEBOARD) -> dict[str, Any]:
    return {**_metadata("voice-manifest", "audio.voice-manifest", task_id, run_id, "clone-voice", engine), "voices": voices}


def storyboard_document(task_id: str, run_id: str, visuals: list[dict[str, Any]], bible: dict[str, Any], engine: Engine = Engine.WHITEBOARD) -> dict[str, Any]:
    return {
        **_metadata("storyboard", "planning.storyboard", task_id, run_id, "plan-storyboard", engine),
        "visual_bible": bible,
        "visuals": visuals,
    }


def illustration_manifest_document(task_id: str, run_id: str, illustrations: list[dict[str, Any]], engine: Engine = Engine.WHITEBOARD) -> dict[str, Any]:
    return {
        **_metadata("illustration-manifest", "illustrations.manifest", task_id, run_id, "generate-illustrations", engine),
        "illustrations": illustrations,
    }


def render_manifest_document(task_id: str, run_id: str, clips: list[dict[str, Any]], engine: Engine = Engine.WHITEBOARD) -> dict[str, Any]:
    return {
        **_metadata("render-manifest", "render.manifest", task_id, run_id, "render-visuals", engine),
        "clips": clips,
    }


def final_manifest_document(
    task_id: str,
    run_id: str,
    video_path: str,
    srt_path: str | None,
    validation: dict[str, Any],
    engine: Engine = Engine.WHITEBOARD,
) -> dict[str, Any]:
    return {
        **_metadata("final-manifest", "output.final-manifest", task_id, run_id, "compose-video", engine),
        "video_path": video_path,
        "srt_path": srt_path,
        "validation": validation,
    }


def json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def _metadata(artifact_type: str, artifact_key: str, task_id: str, run_id: str, stage: str, engine: Engine) -> dict[str, Any]:
    return {
        "schema_version": 1, "artifact_type": artifact_type, "artifact_id": new_id("artifact"), "artifact_key": artifact_key,
        "task_id": task_id, "run_id": run_id, "pipeline_id": "mountain-av-v1", "engine": engine.value,
        "producer_stage": stage, "producer_version": "1.0.0", "created_at": utc_now(), "input_fingerprint": _sha(f"{task_id}:{run_id}:{artifact_key}"),
    }


def _sha(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def save_json_artifact(
    task_id: str,
    run_id: str,
    filename: str,
    data: dict[str, Any],
    stage: str = "unknown",
) -> str:
    """Save a JSON artifact to the run's artifacts directory.

    Returns the artifact key.
    """
    from pathlib import Path

    task_dir = Path("tasks") / task_id
    run_dir = task_dir / "runs" / run_id
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifacts_dir / filename
    artifact_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Derive artifact key from filename
    artifact_key = filename.replace(".json", "").replace("-", ".")
    if stage == "render-visuals":
        artifact_key = "render.manifest"
    elif stage == "compose-video":
        artifact_key = "output.final-manifest"

    return artifact_key


def read_manifest(task_id: str, run_id: str, filename: str) -> dict[str, Any]:
    """Read a JSON manifest from the run's artifacts directory."""
    from pathlib import Path

    task_dir = Path("tasks") / task_id
    run_dir = task_dir / "runs" / run_id
    artifacts_dir = run_dir / "artifacts"

    # Try direct filename first
    artifact_path = artifacts_dir / filename
    if artifact_path.exists():
        return json.loads(artifact_path.read_text(encoding="utf-8"))

    # Try with .json extension if not present
    if not filename.endswith(".json"):
        artifact_path = artifacts_dir / f"{filename}.json"
        if artifact_path.exists():
            return json.loads(artifact_path.read_text(encoding="utf-8"))

    return {}


def _range(value: object) -> dict[str, int]:
    return {"start": value.start, "end": value.end}  # type: ignore[attr-defined]
