from __future__ import annotations

import hashlib
from typing import Any
from csboard.application.av_artifacts import _metadata
from csboard.domain.enums import Engine

def final_manifest_document(project_id: str, run_id: str, timeline: dict[str, Any], render: dict[str, Any], audio_duration_ms: int, tolerance_ms: int = 100) -> dict[str, Any]:
    visual_duration = sum(int(clip["duration_ms"]) for clip in render["clips"])
    timeline_duration = sum(int(unit["duration_ms"]) for unit in timeline["units"])
    delta = abs(audio_duration_ms - visual_duration)
    passed = delta <= tolerance_ms and timeline_duration == visual_duration
    path = "final/final.mp4"
    return {**_metadata("final-manifest", "output.final-manifest", project_id, run_id, "compose-video", Engine.WHITEBOARD), "final_path": path, "sha256": f"sha256:{hashlib.sha256(path.encode()).hexdigest()}", "container": "mp4", "video_codec": "h264", "audio_codec": "aac", "duration_ms": audio_duration_ms, "av_duration_delta_ms": delta, "validation": {"passed": passed, "checks": [{"name": "timeline_matches_clips", "passed": timeline_duration == visual_duration}, {"name": "audio_visual_delta", "passed": delta <= tolerance_ms}]}}

def require_valid_final(document: dict[str, Any]) -> dict[str, Any]:
    if not document["validation"]["passed"]:
        raise ValueError("A/V 校验失败，禁止报告成片成功")
    return document
