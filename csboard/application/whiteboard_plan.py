from __future__ import annotations

from typing import Any

from csboard.application.av_artifacts import _metadata
from csboard.domain.av_timing import VoiceUnit
from csboard.domain.enums import Engine


WHITEBOARD_NEGATIVE = "text, Chinese characters, logo, watermark, photorealistic, 3d render"


def storyboard_document(project_id: str, run_id: str, units: tuple[VoiceUnit, ...], style_profile: str = "whiteboard-default") -> dict[str, Any]:
    visuals: list[dict[str, Any]] = []
    for unit in units:
        for visual in unit.visual_items:
            visuals.append({
                "visual_id": visual.visual_id,
                "unit_id": unit.unit_id,
                "prompt": f"minimal whiteboard illustration, clear visual metaphor for: {visual.text}",
                "negative_prompt": WHITEBOARD_NEGATIVE,
                "composition": "single focal metaphor with generous whitespace",
                "overlay_text": [],
                "style_profile": style_profile,
            })
    return {**_metadata("storyboard", "planning.storyboard", project_id, run_id, "plan-storyboard", Engine.WHITEBOARD), "visuals": visuals}


def storyboard_ids(document: dict[str, Any]) -> set[str]:
    return {str(item["visual_id"]) for item in document["visuals"]}
