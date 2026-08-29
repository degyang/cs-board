"""Storyboard planning service.

Generates visual prompts and visual bible for each Visual Item
based on AV Plan and Timeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from csboard.adapters.filesystem import FilesystemArtifactStore, FilesystemProjectRepository
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.av_artifacts import json_bytes, storyboard_document
from csboard.domain.enums import Engine, StageStatus
from csboard.domain.models import StageState
from csboard.domain.provider_types import TextGenerationRequest
from csboard.ports.providers import TextModelPort


@dataclass
class StoryboardService:
    """Generate visual storyboard from AV Plan and Timeline.

    Parameters
    ----------
    text_model:
        Text model port for generating visual prompts.
    repository:
        Project repository for reading/writing artifacts.
    """

    text_model: TextModelPort
    repository: FilesystemProjectRepository
    artifacts: FilesystemArtifactStore = field(init=False)
    telemetry: JsonlTelemetry = field(init=False)

    def __post_init__(self) -> None:
        self.artifacts = FilesystemArtifactStore(self.repository)
        self.telemetry = JsonlTelemetry(self.repository)

    def run(
        self,
        project_id: str,
        run_id: str,
        engine: Engine = Engine.WHITEBOARD,
    ) -> dict[str, Any]:
        """Generate storyboard for all Visual Items.

        Returns
        -------
        dict with keys: storyboard, visual_count, bible
        """
        # Read dependencies
        av_plan = self._read_artifact(project_id, run_id, "planning.av-plan")
        timeline = self._read_artifact(project_id, run_id, "timing.timeline")

        if not av_plan:
            raise ValueError("请先运行 segment-script 生成 av-plan")
        if not timeline:
            raise ValueError("请先运行 clone-voice 生成 timeline")

        # Build visual items with timing info
        visuals = self._build_visual_list(av_plan, timeline)

        # Generate visual bible
        bible = self._generate_visual_bible(av_plan, visuals)

        # Generate prompts for each visual
        visual_prompts = self._generate_visual_prompts(av_plan, visuals, bible)

        # Build storyboard document
        doc = storyboard_document(project_id, run_id, visual_prompts, bible, engine)

        # Commit artifact
        artifact = self.artifacts.commit_bytes(
            project_id, run_id,
            "planning.storyboard",
            "planning/storyboard.json",
            json_bytes(doc),
            "plan-storyboard",
        )

        return {
            "storyboard": doc,
            "visual_count": len(visual_prompts),
            "bible": bible,
            "artifact_key": artifact.artifact_key,
        }

    def _read_artifact(self, project_id: str, run_id: str, key: str) -> dict[str, Any] | None:
        """Read an artifact by key, returning parsed JSON or None."""
        ref = self.artifacts.get(project_id, run_id, key)
        if not ref:
            return None
        path = self.repository.run_dir(project_id, run_id) / "artifacts" / ref["relative_path"]
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _build_visual_list(
        self,
        av_plan: dict[str, Any],
        timeline: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Build a flat list of visuals with timing info."""
        # Index timeline by unit_id
        timeline_by_unit: dict[str, dict] = {}
        for unit in timeline.get("units", []):
            timeline_by_unit[unit["unit_id"]] = unit

        visuals: list[dict[str, Any]] = []
        for unit in av_plan.get("voice_units", []):
            unit_id = unit["unit_id"]
            unit_timing = timeline_by_unit.get(unit_id, {})
            visual_timings = {
                vt["visual_id"]: vt
                for vt in unit_timing.get("visual_timings", [])
            }

            for visual in unit.get("visual_items", []):
                visual_id = visual["visual_id"]
                timing = visual_timings.get(visual_id, {})
                visuals.append({
                    "visual_id": visual_id,
                    "unit_id": unit_id,
                    "text": visual["text"],
                    "order": visual["order"],
                    "start_ms": timing.get("start_ms", 0),
                    "end_ms": timing.get("end_ms", 0),
                })
        return visuals

    def _generate_visual_bible(
        self,
        av_plan: dict[str, Any],
        visuals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Generate a global visual bible using the text model."""
        # Collect all text for context
        all_text = " ".join(v["text"] for v in visuals)
        engine = av_plan.get("engine", "whiteboard")

        prompt = f"""你是一个视觉风格专家。根据以下旁白内容，生成一个视觉风格指南。

旁白内容：
{all_text[:2000]}

请生成一个 JSON 对象，包含以下字段：
- style: 整体风格描述（如"简约白板手绘风"）
- color_scheme: 色彩方案（主色调、辅助色）
- composition_rules: 构图规则列表
- mood: 情感基调
- visual_metaphors: 视觉隐喻建议

只返回 JSON，不要其他文字。"""

        request = TextGenerationRequest(
            messages=[{"role": "user", "content": prompt}],
            json_schema={
                "type": "object",
                "properties": {
                    "style": {"type": "string"},
                    "color_scheme": {"type": "string"},
                    "composition_rules": {"type": "array", "items": {"type": "string"}},
                    "mood": {"type": "string"},
                    "visual_metaphors": {"type": "array", "items": {"type": "string"}},
                },
            },
            temperature=0.7,
            max_tokens=1024,
        )

        result = self.text_model.generate(request)

        # Parse structured result or fall back to default
        if result.structured_value:
            return result.structured_value
        try:
            return json.loads(result.text)
        except (json.JSONDecodeError, ValueError):
            return {
                "style": "简约白板手绘风" if engine == "whiteboard" else "现代信息图",
                "color_scheme": "黑白为主，点缀彩色",
                "composition_rules": ["居中构图", "留白充足", "重点突出"],
                "mood": "专业、清晰、可信",
                "visual_metaphors": [],
            }

    def _generate_visual_prompts(
        self,
        av_plan: dict[str, Any],
        visuals: list[dict[str, Any]],
        bible: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate prompts for each visual item."""
        style = bible.get("style", "简约白板手绘风")
        color_scheme = bible.get("color_scheme", "黑白为主")

        prompts: list[dict[str, Any]] = []
        for visual in visuals:
            prompt = self._build_single_prompt(visual, style, color_scheme, bible)
            prompts.append({
                "visual_id": visual["visual_id"],
                "unit_id": visual["unit_id"],
                "prompt": prompt,
                "negative_prompt": "text, watermark, logo, blurry, low quality",
                "composition": "centered",
                "overlay_text": [],
                "style_profile": f"{av_plan.get('engine', 'whiteboard')}-v1",
            })
        return prompts

    def _build_single_prompt(
        self,
        visual: dict[str, Any],
        style: str,
        color_scheme: str,
        bible: dict[str, Any],
    ) -> str:
        """Build a prompt for a single visual item."""
        text = visual["text"]
        mood = bible.get("mood", "专业")

        return (
            f"{style}风格，{color_scheme}配色，{mood}氛围。"
            f"画面内容：{text}。"
            f"清晰、简洁、适合作为视频配图。"
        )
