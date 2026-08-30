"""Unit tests for PipelineOrchestrator.

Tests stage dependency resolution, policy behavior, and resume logic.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from csboard.application.pipeline import PipelineOrchestrator, STAGE_ORDER
from csboard.domain.enums import RunStatus, StageStatus
from csboard.domain.models import StageState


def _make_run(stages: dict[str, StageStatus] | None = None, status: str = "pending") -> MagicMock:
    """Create a mock Run object."""
    run = MagicMock()
    run.run_id = "run-test"
    run.task_id = "project-test"
    run.trace_id = "trace-test"
    run.status = RunStatus(status)
    run.stages = {
        name: StageState(StageStatus(stages.get(name, "pending") if stages else "pending"))
        for name in STAGE_ORDER
    }
    return run


class TestStageOrder(unittest.TestCase):
    """Test stage dependency graph."""

    def test_stage_order_has_six_stages(self) -> None:
        self.assertEqual(len(STAGE_ORDER), 6)

    def test_stage_order_starts_with_segment_script(self) -> None:
        self.assertEqual(STAGE_ORDER[0], "segment-script")

    def test_stage_order_ends_with_compose_video(self) -> None:
        self.assertEqual(STAGE_ORDER[-1], "compose-video")


class TestGetNextStage(unittest.TestCase):
    """Test PipelineOrchestrator.get_next_stage()."""

    def test_all_pending_returns_first(self) -> None:
        orch = PipelineOrchestrator(get_run=MagicMock(), save_run=MagicMock(), append_event=MagicMock())
        run = _make_run()
        self.assertEqual(orch.get_next_stage(run), "segment-script")

    def test_first_done_returns_second(self) -> None:
        orch = PipelineOrchestrator(get_run=MagicMock(), save_run=MagicMock(), append_event=MagicMock())
        run = _make_run({"segment-script": "succeeded"})
        self.assertEqual(orch.get_next_stage(run), "clone-voice")

    def test_all_done_returns_none(self) -> None:
        orch = PipelineOrchestrator(get_run=MagicMock(), save_run=MagicMock(), append_event=MagicMock())
        run = _make_run({s: "succeeded" for s in STAGE_ORDER})
        self.assertIsNone(orch.get_next_stage(run))

    def test_failed_stage_returns_it(self) -> None:
        orch = PipelineOrchestrator(get_run=MagicMock(), save_run=MagicMock(), append_event=MagicMock())
        run = _make_run({"segment-script": "succeeded", "clone-voice": "failed"})
        self.assertEqual(orch.get_next_stage(run), "clone-voice")


class TestGetPendingStages(unittest.TestCase):
    """Test PipelineOrchestrator.get_pending_stages()."""

    def test_all_pending(self) -> None:
        orch = PipelineOrchestrator(get_run=MagicMock(), save_run=MagicMock(), append_event=MagicMock())
        run = _make_run()
        pending = orch.get_pending_stages(run)
        self.assertEqual(pending, STAGE_ORDER)

    def test_first_done(self) -> None:
        orch = PipelineOrchestrator(get_run=MagicMock(), save_run=MagicMock(), append_event=MagicMock())
        run = _make_run({"segment-script": "succeeded"})
        pending = orch.get_pending_stages(run)
        self.assertEqual(pending, STAGE_ORDER[1:])

    def test_target_limits_scope(self) -> None:
        orch = PipelineOrchestrator(get_run=MagicMock(), save_run=MagicMock(), append_event=MagicMock())
        run = _make_run()
        pending = orch.get_pending_stages(run, target="clone-voice")
        self.assertEqual(pending, ["segment-script", "clone-voice"])

    def test_all_done_returns_empty(self) -> None:
        orch = PipelineOrchestrator(get_run=MagicMock(), save_run=MagicMock(), append_event=MagicMock())
        run = _make_run({s: "succeeded" for s in STAGE_ORDER})
        pending = orch.get_pending_stages(run)
        self.assertEqual(pending, [])


class TestRunPipeline(unittest.TestCase):
    """Test PipelineOrchestrator.run_pipeline()."""

    def _make_orchestrator(self, executor_results: dict[str, dict] | None = None) -> tuple[PipelineOrchestrator, MagicMock, MagicMock]:
        """Create orchestrator with mock dependencies."""
        run = _make_run()
        get_run = MagicMock(return_value=run)
        save_run = MagicMock()
        append_event = MagicMock(return_value={"sequence": 1})
        orch = PipelineOrchestrator(get_run=get_run, save_run=save_run, append_event=append_event)

        if executor_results:
            for stage, result in executor_results.items():
                orch.register_stage(stage, MagicMock(return_value=result))
        else:
            # Register all stages with success results
            for stage in STAGE_ORDER:
                orch.register_stage(stage, MagicMock(return_value={
                    "ok": True, "command": "stage.run", "stage": stage,
                    "task_id": "project-test", "run_id": "run-test",
                }))
        return orch, get_run, save_run

    def test_auto_runs_all_stages(self) -> None:
        orch, _, _ = self._make_orchestrator()
        result = orch.run_pipeline("project-test", "run-test", policy="auto")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["stages_executed"]), 6)

    def test_gated_runs_one_stage(self) -> None:
        orch, _, _ = self._make_orchestrator()
        result = orch.run_pipeline("project-test", "run-test", policy="gated")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["stages_executed"]), 1)
        self.assertEqual(result["stages_executed"][0], "segment-script")

    def test_targeted_runs_target_with_missing_dependencies(self) -> None:
        orch, _, _ = self._make_orchestrator()
        result = orch.run_pipeline("project-test", "run-test", policy="targeted", target_stage="clone-voice")
        self.assertTrue(result["ok"])
        self.assertEqual(result["stages_executed"], ["segment-script", "clone-voice"])

    def test_targeted_requires_stage(self) -> None:
        orch, _, _ = self._make_orchestrator()
        from csboard.domain.errors import DomainError
        with self.assertRaises(DomainError):
            orch.run_pipeline("project-test", "run-test", policy="targeted")

    def test_invalid_policy_raises(self) -> None:
        orch, _, _ = self._make_orchestrator()
        from csboard.domain.errors import DomainError
        with self.assertRaises(DomainError):
            orch.run_pipeline("project-test", "run-test", policy="bogus")

    def test_unregistered_stage_returns_capability_error(self) -> None:
        orch, _, _ = self._make_orchestrator()
        # Don't register any stages
        orch._executors.clear()
        result = orch.run_pipeline("project-test", "run-test", policy="targeted", target_stage="segment-script")
        self.assertFalse(result["ok"])
        self.assertEqual(result["results"][0]["error"]["code"], "CAPABILITY_NOT_AVAILABLE")

    def test_stage_failure_stops_pipeline(self) -> None:
        orch, _, _ = self._make_orchestrator({
            "segment-script": {"ok": True, "command": "stage.run", "stage": "segment-script", "task_id": "p", "run_id": "r"},
            "clone-voice": {"ok": False, "command": "stage.run", "stage": "clone-voice", "task_id": "p", "run_id": "r",
                            "error": {"code": "TTS_FAILED", "message": "TTS failed", "retryable": True}},
        })
        result = orch.run_pipeline("project-test", "run-test", policy="auto")
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["stages_executed"]), 2)


class TestResumePipeline(unittest.TestCase):
    """Test PipelineOrchestrator.resume_pipeline()."""

    def test_resume_from_failed(self) -> None:
        run = _make_run(
            {"segment-script": "succeeded", "clone-voice": "failed"},
            status="failed",
        )
        get_run = MagicMock(return_value=run)
        save_run = MagicMock()
        append_event = MagicMock(return_value={"sequence": 1})
        orch = PipelineOrchestrator(get_run=get_run, save_run=save_run, append_event=append_event)
        orch.register_stage("clone-voice", MagicMock(return_value={
            "ok": True, "command": "stage.run", "stage": "clone-voice",
            "task_id": "project-test", "run_id": "run-test",
        }))
        for stage in STAGE_ORDER[2:]:
            orch.register_stage(stage, MagicMock(return_value={
                "ok": True, "command": "stage.run", "stage": stage,
                "task_id": "project-test", "run_id": "run-test",
            }))

        result = orch.resume_pipeline("project-test", "run-test")
        self.assertTrue(result["ok"])
        self.assertIn("clone-voice", result["stages_executed"])

    def test_resume_completed_is_noop(self) -> None:
        run = _make_run({s: "succeeded" for s in STAGE_ORDER}, status="succeeded")
        get_run = MagicMock(return_value=run)
        save_run = MagicMock()
        append_event = MagicMock(return_value={"sequence": 1})
        orch = PipelineOrchestrator(get_run=get_run, save_run=save_run, append_event=append_event)

        result = orch.resume_pipeline("project-test", "run-test")
        self.assertTrue(result["ok"])
        self.assertEqual(result["stages_executed"], [])


class TestNextStageAfter(unittest.TestCase):
    """Test PipelineOrchestrator._next_stage_after()."""

    def test_first_returns_second(self) -> None:
        self.assertEqual(PipelineOrchestrator._next_stage_after("segment-script"), "clone-voice")

    def test_last_returns_none(self) -> None:
        self.assertIsNone(PipelineOrchestrator._next_stage_after("compose-video"))

    def test_unknown_returns_none(self) -> None:
        self.assertIsNone(PipelineOrchestrator._next_stage_after("nonexistent"))


if __name__ == "__main__":
    unittest.main()
