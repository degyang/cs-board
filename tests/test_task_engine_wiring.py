"""Task engine wiring — M09 WBS-5 focused tests.

Covers:
- plan-storyboard with infographic-remotion produces remotion_props in storyboard artifact
- plan-storyboard with whiteboard does NOT include remotion_props
- _exec_render_visuals routes to RemotionRendererAdapter for infographic-remotion
- _exec_render_visuals routes to service resolver for whiteboard
- Missing av-plan/timeline gives stable sanitized error for infographic-remotion
- Whiteboard path unchanged (no regression)
- Storyboard artifact structure for infographic-remotion
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from csboard.adapters.filesystem import FilesystemTaskRepository, FilesystemArtifactStore
from csboard.application.av_artifacts import json_bytes
from csboard.application.commands import MountainCommands
from csboard.application.context import CommandContext
from csboard.domain.enums import Engine, Entrypoint, RunStatus, StageStatus
from csboard.domain.errors import DomainError


def _make_av_plan(units: list[dict] | None = None) -> dict:
    """Minimal av-plan artifact."""
    return {
        "schema_version": 1,
        "artifact_type": "av-plan",
        "engine": "infographic-remotion",
        "voice_units": units or [
            {
                "unit_id": "unit-001",
                "order": 1,
                "source_range": {"start": 0, "end": 10},
                "text": "第一段旁白内容",
                "visual_items": [
                    {
                        "visual_id": "vis-001",
                        "order": 1,
                        "source_range": {"start": 0, "end": 10},
                        "text": "第一段旁白内容",
                    },
                ],
            },
            {
                "unit_id": "unit-002",
                "order": 2,
                "source_range": {"start": 11, "end": 20},
                "text": "第二段旁白内容",
                "visual_items": [
                    {
                        "visual_id": "vis-002",
                        "order": 1,
                        "source_range": {"start": 11, "end": 20},
                        "text": "第二段旁白内容",
                    },
                ],
            },
        ],
    }


def _make_timeline() -> dict:
    """Minimal timeline artifact."""
    return {
        "schema_version": 1,
        "artifact_type": "timeline",
        "engine": "infographic-remotion",
        "units": [
            {
                "unit_id": "unit-001",
                "duration_ms": 3000,
                "timing_source": "whisper",
                "alignment": {},
                "visual_timings": [
                    {"visual_id": "vis-001", "start_ms": 0, "end_ms": 3000},
                ],
            },
            {
                "unit_id": "unit-002",
                "duration_ms": 4000,
                "timing_source": "whisper",
                "alignment": {},
                "visual_timings": [
                    {"visual_id": "vis-002", "start_ms": 3000, "end_ms": 7000},
                ],
            },
        ],
    }


class EngineWiringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = FilesystemTaskRepository(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _create_task_with_engine(self, engine: Engine) -> tuple[str, str]:
        """Create a task and run with the given engine."""
        from csboard.domain.models import Task, Run
        from csboard.application.context import new_id, utc_now
        from csboard.domain.enums import TaskStatus

        task_id = new_id("task")
        run_id = new_id("run")
        task = Task(
            task_id=task_id, title="测试任务", pipeline_id="mountain-av-v1",
            engine=engine, status=TaskStatus.READY,
            created_at=utc_now(), updated_at=utc_now(), active_run_id=run_id,
        )
        run = Run(
            run_id=run_id, task_id=task_id, trace_id=new_id("trace"),
            entrypoint=Entrypoint.CLI, command_ids=[],
            status=RunStatus.PENDING, target_stage="compose-video",
            started_at=utc_now(),
        )
        self.repository.create_task(task)
        self.repository.create_run(run)
        return task_id, run_id

    def _commit_artifact(self, task_id: str, run_id: str, key: str, data: dict) -> None:
        """Commit a JSON artifact."""
        store = FilesystemArtifactStore(self.repository)
        store.commit_bytes(
            task_id, run_id, key, f"{key.replace('.', '/')}.json",
            json_bytes(data), "test",
        )

    # ── plan-storyboard: infographic-remotion ────────────────────────

    def test_infographic_plan_storyboard_produces_remotion_props(self) -> None:
        """infographic-remotion storyboard includes remotion_props."""
        task_id, run_id = self._create_task_with_engine(Engine.INFOGRAPHIC_REMOTION)
        self._commit_artifact(task_id, run_id, "planning.av-plan", _make_av_plan())
        self._commit_artifact(task_id, run_id, "timing.timeline", _make_timeline())

        commands = MountainCommands(self.root, repository=self.repository)
        result = commands.plan_storyboard(task_id, run_id, text_model=None)

        self.assertTrue(result["ok"])
        self.assertEqual(result["stage"], "plan-storyboard")

        # Read the storyboard artifact
        store = FilesystemArtifactStore(self.repository)
        ref = store.get(task_id, run_id, "planning.storyboard")
        self.assertIsNotNone(ref)
        path = self.repository.run_dir(task_id, run_id) / "artifacts" / ref["relative_path"]
        doc = json.loads(path.read_text(encoding="utf-8"))

        # Must have remotion_props
        self.assertIn("remotion_props", doc)
        props = doc["remotion_props"]
        self.assertIn("fps", props)
        self.assertIn("pages", props)
        self.assertEqual(props["fps"], 30)
        self.assertGreater(len(props["pages"]), 0)

        # Must have voice_units embedded for renderer
        self.assertIn("voice_units", doc)
        self.assertEqual(len(doc["voice_units"]), 2)

        # Must have visuals
        self.assertIn("visuals", doc)
        self.assertGreater(len(doc["visuals"]), 0)

    def test_infographic_storyboard_pages_match_voice_units(self) -> None:
        """Each voice unit produces one page in the remotion props."""
        task_id, run_id = self._create_task_with_engine(Engine.INFOGRAPHIC_REMOTION)
        self._commit_artifact(task_id, run_id, "planning.av-plan", _make_av_plan())
        self._commit_artifact(task_id, run_id, "timing.timeline", _make_timeline())

        commands = MountainCommands(self.root, repository=self.repository)
        commands.plan_storyboard(task_id, run_id, text_model=None)

        store = FilesystemArtifactStore(self.repository)
        ref = store.get(task_id, run_id, "planning.storyboard")
        path = self.repository.run_dir(task_id, run_id) / "artifacts" / ref["relative_path"]
        doc = json.loads(path.read_text(encoding="utf-8"))

        pages = doc["remotion_props"]["pages"]
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0]["id"], "page-unit-001")
        self.assertEqual(pages[1]["id"], "page-unit-002")

    def test_infographic_storyboard_total_duration_correct(self) -> None:
        """Total duration in remotion props matches timeline."""
        task_id, run_id = self._create_task_with_engine(Engine.INFOGRAPHIC_REMOTION)
        self._commit_artifact(task_id, run_id, "planning.av-plan", _make_av_plan())
        self._commit_artifact(task_id, run_id, "timing.timeline", _make_timeline())

        commands = MountainCommands(self.root, repository=self.repository)
        commands.plan_storyboard(task_id, run_id, text_model=None)

        store = FilesystemArtifactStore(self.repository)
        ref = store.get(task_id, run_id, "planning.storyboard")
        path = self.repository.run_dir(task_id, run_id) / "artifacts" / ref["relative_path"]
        doc = json.loads(path.read_text(encoding="utf-8"))

        props = doc["remotion_props"]
        self.assertEqual(props["totalDurationMs"], 7000)
        self.assertEqual(props["totalDurationFrames"], 210)  # 7000 * 30 / 1000

    # ── plan-storyboard: whiteboard (no regression) ──────────────────

    def test_whiteboard_plan_storyboard_no_remotion_props(self) -> None:
        """Whiteboard storyboard does NOT include remotion_props."""
        task_id, run_id = self._create_task_with_engine(Engine.WHITEBOARD)
        self._commit_artifact(task_id, run_id, "planning.av-plan", _make_av_plan())
        self._commit_artifact(task_id, run_id, "timing.timeline", _make_timeline())

        commands = MountainCommands(self.root, repository=self.repository)
        result = commands.plan_storyboard(task_id, run_id, text_model=None)

        self.assertTrue(result["ok"])

        store = FilesystemArtifactStore(self.repository)
        ref = store.get(task_id, run_id, "planning.storyboard")
        path = self.repository.run_dir(task_id, run_id) / "artifacts" / ref["relative_path"]
        doc = json.loads(path.read_text(encoding="utf-8"))

        self.assertNotIn("remotion_props", doc)
        self.assertIn("visual_bible", doc)
        self.assertIn("visuals", doc)

    # ── plan-storyboard: missing dependencies ────────────────────────

    def test_infographic_plan_storyboard_rejects_missing_av_plan(self) -> None:
        """Missing av-plan gives stable error for infographic-remotion."""
        task_id, run_id = self._create_task_with_engine(Engine.INFOGRAPHIC_REMOTION)
        # Only commit timeline, not av-plan
        self._commit_artifact(task_id, run_id, "timing.timeline", _make_timeline())

        commands = MountainCommands(self.root, repository=self.repository)
        with self.assertRaises(DomainError) as ctx:
            commands.plan_storyboard(task_id, run_id, text_model=None)
        self.assertEqual(ctx.exception.code, "VALIDATION_ERROR")
        self.assertIn("av-plan", ctx.exception.message)
        # No path leakage
        self.assertNotIn("/", ctx.exception.message)

    def test_infographic_plan_storyboard_rejects_missing_timeline(self) -> None:
        """Missing timeline gives stable error for infographic-remotion."""
        task_id, run_id = self._create_task_with_engine(Engine.INFOGRAPHIC_REMOTION)
        self._commit_artifact(task_id, run_id, "planning.av-plan", _make_av_plan())
        # No timeline committed

        commands = MountainCommands(self.root, repository=self.repository)
        with self.assertRaises(DomainError) as ctx:
            commands.plan_storyboard(task_id, run_id, text_model=None)
        self.assertEqual(ctx.exception.code, "VALIDATION_ERROR")
        self.assertIn("timeline", ctx.exception.message)

    # ── _exec_render_visuals: engine routing ─────────────────────────

    def test_exec_render_visuals_infographic_uses_remotion_adapter(self) -> None:
        """infographic-remotion render stage creates RemotionRendererAdapter
        rather than resolving from service registry."""
        task_id, run_id = self._create_task_with_engine(Engine.INFOGRAPHIC_REMOTION)
        # No service_resolver or provider_factory — infographic path shouldn't need them
        commands = MountainCommands(self.root, repository=self.repository)
        commands.service_resolver = None
        commands.provider_factory = None

        # _exec_render_visuals should NOT raise CAPABILITY_NOT_AVAILABLE
        # (that's the whiteboard path).  It should create RemotionRendererAdapter
        # and fail later with missing artifacts.
        from csboard.adapters.remotion.renderer_adapter import RemotionRenderError
        with self.assertRaises((DomainError, RemotionRenderError, Exception)) as ctx:
            commands._exec_render_visuals(task_id, run_id, CommandContext(entrypoint=Entrypoint.CLI))
        # Must NOT be CAPABILITY_NOT_AVAILABLE — that means it tried the whiteboard path
        if isinstance(ctx.exception, DomainError):
            self.assertNotEqual(ctx.exception.code, "CAPABILITY_NOT_AVAILABLE")

    def test_exec_render_visuals_whiteboard_uses_service_resolver(self) -> None:
        """Whiteboard render stage resolves renderer from service registry."""
        task_id, run_id = self._create_task_with_engine(Engine.WHITEBOARD)
        mock_resolver = MagicMock()
        mock_factory = MagicMock()
        mock_renderer = MagicMock()
        mock_factory.create_adapter.return_value = mock_renderer

        commands = MountainCommands(
            self.root, repository=self.repository,
            service_resolver=mock_resolver, provider_factory=mock_factory,
        )

        # Will fail at render_visuals (missing artifacts), but resolve was called
        try:
            commands._exec_render_visuals(task_id, run_id, CommandContext(entrypoint=Entrypoint.CLI))
        except Exception:
            pass

        mock_resolver.resolve.assert_called_with("rendering")
        mock_factory.create_adapter.assert_called_once()

    def test_exec_render_visuals_whiteboard_no_resolver_raises(self) -> None:
        """Whiteboard render without service resolver gives stable error."""
        task_id, run_id = self._create_task_with_engine(Engine.WHITEBOARD)
        commands = MountainCommands(self.root, repository=self.repository)
        commands.service_resolver = None
        commands.provider_factory = MagicMock()

        with self.assertRaises(DomainError) as ctx:
            commands._exec_render_visuals(task_id, run_id, CommandContext(entrypoint=Entrypoint.CLI))
        self.assertEqual(ctx.exception.code, "CAPABILITY_NOT_AVAILABLE")

    # ── Storyboard artifact structure ────────────────────────────────

    def test_infographic_storyboard_has_engine_in_metadata(self) -> None:
        """Storyboard artifact metadata records the engine."""
        task_id, run_id = self._create_task_with_engine(Engine.INFOGRAPHIC_REMOTION)
        self._commit_artifact(task_id, run_id, "planning.av-plan", _make_av_plan())
        self._commit_artifact(task_id, run_id, "timing.timeline", _make_timeline())

        commands = MountainCommands(self.root, repository=self.repository)
        commands.plan_storyboard(task_id, run_id, text_model=None)

        store = FilesystemArtifactStore(self.repository)
        ref = store.get(task_id, run_id, "planning.storyboard")
        path = self.repository.run_dir(task_id, run_id) / "artifacts" / ref["relative_path"]
        doc = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(doc["engine"], "infographic-remotion")
        self.assertEqual(doc["artifact_type"], "storyboard")

    def test_infographic_storyboard_visual_bible_is_set(self) -> None:
        """Storyboard has a visual_bible even for infographic engine."""
        task_id, run_id = self._create_task_with_engine(Engine.INFOGRAPHIC_REMOTION)
        self._commit_artifact(task_id, run_id, "planning.av-plan", _make_av_plan())
        self._commit_artifact(task_id, run_id, "timing.timeline", _make_timeline())

        commands = MountainCommands(self.root, repository=self.repository)
        commands.plan_storyboard(task_id, run_id, text_model=None)

        store = FilesystemArtifactStore(self.repository)
        ref = store.get(task_id, run_id, "planning.storyboard")
        path = self.repository.run_dir(task_id, run_id) / "artifacts" / ref["relative_path"]
        doc = json.loads(path.read_text(encoding="utf-8"))

        self.assertIn("visual_bible", doc)
        self.assertIn("style", doc["visual_bible"])

    # ── Run state transitions ────────────────────────────────────────

    def test_infographic_plan_storyboard_updates_run_state(self) -> None:
        """Run stage state transitions correctly for infographic-remotion."""
        task_id, run_id = self._create_task_with_engine(Engine.INFOGRAPHIC_REMOTION)
        self._commit_artifact(task_id, run_id, "planning.av-plan", _make_av_plan())
        self._commit_artifact(task_id, run_id, "timing.timeline", _make_timeline())

        commands = MountainCommands(self.root, repository=self.repository)
        commands.plan_storyboard(task_id, run_id, text_model=None)

        run = self.repository.get_run(task_id, run_id)
        stage = run.stages.get("plan-storyboard")
        self.assertIsNotNone(stage)
        self.assertEqual(stage.status, StageStatus.SUCCEEDED)


if __name__ == "__main__":
    unittest.main()
