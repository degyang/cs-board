from __future__ import annotations

import hashlib
import json
from typing import Any

from csboard.application.context import new_id, utc_now
from csboard.domain.av_timing import UnitTiming, VoiceUnit
from csboard.domain.enums import Engine


def av_plan_document(project_id: str, run_id: str, units: tuple[VoiceUnit, ...], source_text: str, engine: Engine = Engine.WHITEBOARD) -> dict[str, Any]:
    return {
        **_metadata("av-plan", "planning.av-plan", project_id, run_id, "segment-script", engine),
        "source_text_sha256": _sha(source_text),
        "voice_units": [{
            "unit_id": unit.unit_id, "order": unit.order, "source_range": _range(unit.source_range), "text": unit.text,
            "visual_items": [{"visual_id": item.visual_id, "order": item.order, "source_range": _range(item.source_range), "text": item.text} for item in unit.visual_items],
        } for unit in units],
    }


def timeline_document(project_id: str, run_id: str, timings: tuple[UnitTiming, ...], engine: Engine = Engine.WHITEBOARD) -> dict[str, Any]:
    return {
        **_metadata("timeline", "timing.timeline", project_id, run_id, "clone-voice", engine),
        "units": [{
            "unit_id": item.unit_id, "duration_ms": item.duration_ms, "timing_source": item.timing_source.value,
            "alignment": item.alignment,
            "visual_timings": [{"visual_id": visual.visual_id, "start_ms": visual.start_ms, "end_ms": visual.end_ms} for visual in item.visual_timings],
        } for item in timings],
    }


def json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")


def _metadata(artifact_type: str, artifact_key: str, project_id: str, run_id: str, stage: str, engine: Engine) -> dict[str, Any]:
    return {
        "schema_version": 1, "artifact_type": artifact_type, "artifact_id": new_id("artifact"), "artifact_key": artifact_key,
        "project_id": project_id, "run_id": run_id, "pipeline_id": "mountain-av-v1", "engine": engine.value,
        "producer_stage": stage, "producer_version": "1.0.0", "created_at": utc_now(), "input_fingerprint": _sha(f"{project_id}:{run_id}:{artifact_key}"),
    }


def _sha(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _range(value: object) -> dict[str, int]:
    return {"start": value.start, "end": value.end}  # type: ignore[attr-defined]
