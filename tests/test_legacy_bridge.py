from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from csboard.application import LegacyJobBridge
from csboard.domain.enums import Engine, RunStatus


class LegacyBridgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.bridge = LegacyJobBridge(Path(self.temporary.name))
        self.job = {
            "id": "legacy-job-1",
            "task_name": "历史标准任务",
            "status": "queued",
            "stage": "等待语音克隆",
            "progress": 1,
            "queue_stage": "voice",
            "copy": "这段文案不应被写入诊断事件。",
            "reference_mode": "standard",
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_sync_creates_stable_read_compatible_link(self) -> None:
        first = self.bridge.sync("legacy-job-1", self.job)
        second = self.bridge.sync("legacy-job-1", self.job)
        project = self.bridge.repository.get_task(first.task_id)
        run = self.bridge.repository.get_run(first.task_id, first.run_id)
        events = self.bridge.telemetry.read_events(first.task_id, first.run_id)

        self.assertEqual(first, second)
        self.assertEqual(project.engine, Engine.WHITEBOARD)
        self.assertEqual(run.status, RunStatus.PENDING)
        self.assertEqual(len(events), 1)
        self.assertNotIn("copy", events[0])
        self.assertEqual(self.job["_mountain"]["trace_id"], first.trace_id)

    def test_status_transition_writes_correlated_event_without_rewriting_legacy_media(self) -> None:
        link = self.bridge.sync("legacy-job-1", self.job)
        self.job.update(status="running", stage="语音生成中", progress=8, current_phase="voice")
        self.bridge.sync("legacy-job-1", self.job, action="legacy.voice.start")
        run = self.bridge.repository.get_run(link.task_id, link.run_id)
        events = self.bridge.telemetry.read_events(link.task_id, link.run_id)

        self.assertEqual(run.status, RunStatus.RUNNING)
        self.assertEqual([event["sequence"] for event in events], [1, 2])
        self.assertEqual(events[-1]["action"], "legacy.voice.start")
        self.assertEqual(events[-1]["trace_id"], link.trace_id)
        self.assertFalse((Path(self.temporary.name) / "jobs" / "legacy-job-1").exists())

    def test_infographic_job_uses_explicit_legacy_pipeline(self) -> None:
        self.job.update(job_type="infographic", reference_mode="infographic")
        link = self.bridge.sync("legacy-job-1", self.job)
        project = self.bridge.repository.get_task(link.task_id)

        self.assertEqual(link.pipeline_id, "infographic-remotion-v8")
        self.assertEqual(project.engine, Engine.INFOGRAPHIC_REMOTION)


if __name__ == "__main__":
    unittest.main()
