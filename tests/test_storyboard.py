"""Unit tests for StoryboardService.

Uses FakeTextModel to avoid real LLM calls.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from csboard.adapters.fakes import FakeTextModel
from csboard.adapters.filesystem import FilesystemTaskRepository, FilesystemArtifactStore
from csboard.application.av_artifacts import av_plan_document, json_bytes, timeline_document
from csboard.application.context import new_id, utc_now
from csboard.application.storyboard import StoryboardService
from csboard.domain.av_timing import TextRange, VisualItem, VoiceUnit
from csboard.domain.enums import Engine, Entrypoint, TaskStatus, RunStatus, StageStatus
from csboard.domain.models import Task, Run, StageState


def _setup_project(root: Path) -> tuple[str, str, FilesystemTaskRepository]:
    """Create a test project with av-plan and timeline artifacts."""
    repo = FilesystemTaskRepository(root)
    task_id = new_id("project")
    run_id = new_id("run")

    # Create project
    task = Task(
        task_id=task_id,
        title="测试项目",
        pipeline_id="mountain-av-v1",
        engine=Engine.WHITEBOARD,
        status=TaskStatus.READY,
        created_at=utc_now(),
        updated_at=utc_now(),
        active_run_id=run_id,
    )
    repo.create_task(task)

    # Create run
    run = Run(
        run_id=run_id,
        task_id=task_id,
        trace_id=new_id("trace"),
        entrypoint=Entrypoint.CLI,
        command_ids=[new_id("command")],
        status=RunStatus.RUNNING,
        target_stage="compose-video",
        started_at=utc_now(),
        stages={
            "generate-visual-anchors": StageState(StageStatus.SUCCEEDED, 1),
            "clone-voice": StageState(StageStatus.SUCCEEDED, 1),
        },
    )
    repo.create_run(run)

    # Create av-plan artifact
    units = (
        VoiceUnit(
            unit_id="unit-001",
            order=1,
            source_range=TextRange(0, 20),
            text="这是第一段测试文案内容。",
            visual_items=(
                VisualItem("visual-001-01", 1, TextRange(0, 10), "这是第一段"),
                VisualItem("visual-001-02", 2, TextRange(10, 20), "测试文案内容"),
            ),
        ),
    )
    av_plan = av_plan_document(task_id, run_id, units, "这是第一段测试文案内容。", Engine.WHITEBOARD)
    store = FilesystemArtifactStore(repo)
    store.commit_bytes(
        task_id, run_id, "planning.av-plan", "planning/av-plan.json",
        json_bytes(av_plan), "generate-visual-anchors",
    )

    # Create timeline artifact
    from csboard.domain.av_timing import UnitTiming, VisualTiming
    from csboard.domain.enums import TimingSource
    timings = (
        UnitTiming(
            unit_id="unit-001",
            duration_ms=5000,
            timing_source=TimingSource.EQUAL_FALLBACK,
            alignment={"status": "succeeded"},
            visual_timings=(
                VisualTiming("visual-001-01", 0, 2500),
                VisualTiming("visual-001-02", 2500, 5000),
            ),
        ),
    )
    timeline = timeline_document(task_id, run_id, timings, Engine.WHITEBOARD)
    store.commit_bytes(
        task_id, run_id, "timing.timeline", "planning/timeline.json",
        json_bytes(timeline), "clone-voice",
    )

    return task_id, run_id, repo


class TestStoryboardService(unittest.TestCase):
    """Test StoryboardService.run()."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.task_id, self.run_id, self.repo = _setup_project(self.root)
        self.text_model = FakeTextModel()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_returns_storyboard(self) -> None:
        service = StoryboardService(self.text_model, self.repo)
        result = service.run(self.task_id, self.run_id)
        self.assertIn("storyboard", result)

    def test_visual_count_matches(self) -> None:
        service = StoryboardService(self.text_model, self.repo)
        result = service.run(self.task_id, self.run_id)
        self.assertEqual(result["visual_count"], 2)

    def test_bible_generated(self) -> None:
        # Use a text model that returns a valid bible structure
        bible_response = '{"style": "简约白板手绘风", "color_scheme": "黑白为主", "composition_rules": ["居中构图"], "mood": "专业", "visual_metaphors": []}'
        text_model = FakeTextModel(response_text=bible_response)
        service = StoryboardService(text_model, self.repo)
        result = service.run(self.task_id, self.run_id)
        self.assertIn("bible", result)
        self.assertIn("style", result["bible"])

    def test_missing_optional_text_model_uses_saved_style_context(self) -> None:
        service = StoryboardService(None, self.repo, {"style": "粗线条科学白板风"})
        result = service.run(self.task_id, self.run_id)
        self.assertEqual(result["bible"]["style"], "粗线条科学白板风")
        self.assertTrue(all("粗线条科学白板风" in item["prompt"] for item in result["storyboard"]["visuals"]))

    def test_artifact_committed(self) -> None:
        service = StoryboardService(self.text_model, self.repo)
        result = service.run(self.task_id, self.run_id)
        store = FilesystemArtifactStore(self.repo)
        ref = store.get(self.task_id, self.run_id, "planning.storyboard")
        self.assertIsNotNone(ref)

    def test_visuals_have_prompts(self) -> None:
        service = StoryboardService(self.text_model, self.repo)
        result = service.run(self.task_id, self.run_id)
        visuals = result["storyboard"]["visuals"]
        for visual in visuals:
            self.assertIn("prompt", visual)
            self.assertIn("visual_id", visual)

    def test_missing_av_plan_raises(self) -> None:
        # Create a project without av-plan
        task_id = new_id("project")
        run_id = new_id("run")
        task = Task(
            task_id=task_id,
            title="测试项目",
            pipeline_id="mountain-av-v1",
            engine=Engine.WHITEBOARD,
            status=TaskStatus.READY,
            created_at=utc_now(),
            updated_at=utc_now(),
            active_run_id=run_id,
        )
        self.repo.create_task(task)
        run = Run(
            run_id=run_id, task_id=task_id, trace_id=new_id("trace"),
            entrypoint=Entrypoint.CLI, command_ids=[], status=RunStatus.RUNNING,
            target_stage="compose-video", started_at=utc_now(),
        )
        self.repo.create_run(run)

        service = StoryboardService(self.text_model, self.repo)
        with self.assertRaises(ValueError):
            service.run(task_id, run_id)


if __name__ == "__main__":
    unittest.main()
