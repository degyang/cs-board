from __future__ import annotations

import hashlib
from typing import Any

from csboard.application.av_artifacts import _metadata
from csboard.domain.enums import Engine


def render_manifest_document(project_id: str, run_id: str, timeline: dict[str, Any], illustrations: dict[str, Any], fps: int = 30) -> dict[str, Any]:
    image_by_visual = {item["visual_id"]: item for item in illustrations["illustrations"]}
    clips = []
    for unit in timeline["units"]:
        for timing in unit["visual_timings"]:
            visual_id = timing["visual_id"]
            if visual_id not in image_by_visual:
                raise ValueError(f"缺少 Visual 插画：{visual_id}")
            duration = int(timing["end_ms"]) - int(timing["start_ms"])
            if duration <= 0:
                raise ValueError(f"Visual 时间无效：{visual_id}")
            path = f"clips/{visual_id}.mp4"
            clips.append({"visual_id": visual_id, "clip_path": path, "sha256": f"sha256:{hashlib.sha256(path.encode()).hexdigest()}", "duration_ms": duration})
    return {**_metadata("render-manifest", "render.manifest", project_id, run_id, "render-visuals", Engine.WHITEBOARD), "renderer": "whiteboard", "canvas": {"width": 1920, "height": 1080}, "fps": fps, "clips": clips}
