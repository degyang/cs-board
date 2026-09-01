from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from csboard.adapters.filesystem import FilesystemArtifactStore, FilesystemTaskRepository
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.context import CommandContext, new_id, utc_now
from csboard.domain.enums import Engine, Entrypoint, TaskStatus, RunStatus
from csboard.domain.errors import DomainError
from csboard.domain.models import Task, Run


class FoundationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = FilesystemTaskRepository(self.root)
        self.task_id = new_id("project")
        self.run_id = new_id("run")
        self.task = Task(
            task_id=self.task_id,
            title="标准流程测试",
            pipeline_id="standard-whiteboard",
            engine=Engine.WHITEBOARD,
            status=TaskStatus.DRAFT,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        self.repository.create_task(self.task)
        context = CommandContext(entrypoint=Entrypoint.CLI)
        self.run = Run(
            run_id=self.run_id,
            task_id=self.task_id,
            trace_id=new_id("trace"),
            entrypoint=context.entrypoint,
            command_ids=[context.command_id],
            status=RunStatus.RUNNING,
            target_stage="render",
            started_at=utc_now(),
        )
        self.repository.create_run(self.run)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_project_and_run_are_persisted_with_correlation(self) -> None:
        stored_project = self.repository.get_task(self.task_id)
        stored_run = self.repository.get_run(self.task_id, self.run_id)

        self.assertEqual(stored_project.engine, Engine.WHITEBOARD)
        self.assertEqual(stored_run.trace_id, self.run.trace_id)
        self.assertEqual(stored_run.command_ids, self.run.command_ids)
        self.assertTrue((self.repository.run_dir(self.task_id, self.run_id) / "artifacts" / "index.json").exists())

    def test_artifact_commit_is_atomic_and_invalidates_only_downstream(self) -> None:
        store = FilesystemArtifactStore(self.repository)
        plan = b'{"voice_units": []}'
        store.commit_bytes(self.task_id, self.run_id, "planning.av-plan", "plans/av-plan.json", plan, "plan")
        store.commit_bytes(self.task_id, self.run_id, "audio.voice-manifest", "audio/voice.json", b"{}", "voice")
        store.commit_bytes(self.task_id, self.run_id, "timing.timeline", "timing/timeline.json", b"{}", "timing")

        invalidated = store.invalidate_from(self.task_id, self.run_id, "planning.av-plan", "plan changed")
        ref = store.get(self.task_id, self.run_id, "planning.av-plan")
        timeline = store.get(self.task_id, self.run_id, "timing.timeline")
        target = self.repository.run_dir(self.task_id, self.run_id) / "artifacts" / "plans" / "av-plan.json"

        self.assertEqual(ref["sha256"], hashlib.sha256(plan).hexdigest())
        self.assertEqual(ref["status"], "succeeded")
        self.assertEqual(timeline["status"], "stale")
        self.assertEqual(invalidated, ["audio.voice-manifest", "timing.timeline"])
        self.assertEqual(target.read_bytes(), plan)
        self.assertFalse(list(target.parent.glob("*.partial")))

    def test_artifact_paths_cannot_escape_project(self) -> None:
        store = FilesystemArtifactStore(self.repository)
        for path in ("../escape.json", "C:\\escape.json", "nested\\escape.json"):
            with self.subTest(path=path), self.assertRaises(DomainError) as context:
                store.commit_bytes(self.task_id, self.run_id, "bad", path, b"bad", "test")
            self.assertEqual(context.exception.code, "INVALID_ARTIFACT_PATH")

    def test_jsonl_telemetry_is_ordered_and_redacted(self) -> None:
        telemetry = JsonlTelemetry(self.repository)
        first = telemetry.append_event(self.task_id, self.run_id, {"event_type": "RunStarted"})
        second = telemetry.append_event(self.task_id, self.run_id, {"event_type": "StageStarted"})
        telemetry.append_log(self.task_id, self.run_id, {"level": "info", "api_key": "canary-secret-123"})
        telemetry.append_audit(self.task_id, self.run_id, {"action": "run.start", "authorization": "Bearer canary-secret-123"})

        events = telemetry.read_events(self.task_id, self.run_id, after_sequence=1)
        logs = (self.repository.run_dir(self.task_id, self.run_id) / "observability" / "logs.jsonl").read_text(encoding="utf-8")
        self.assertEqual(first["sequence"], 1)
        self.assertEqual(second["sequence"], 2)
        self.assertEqual(events, [second])
        self.assertNotIn("canary-secret-123", logs)
        self.assertIn("[REDACTED]", logs)

    def test_diagnostic_bundle_excludes_media_and_redacts_data(self) -> None:
        telemetry = JsonlTelemetry(self.repository)
        telemetry.append_log(self.task_id, self.run_id, {"token": "canary-secret-123"})
        media = self.repository.run_dir(self.task_id, self.run_id) / "media" / "source.wav"
        media.write_bytes(b"private-audio")

        bundle = telemetry.export_diagnostic_bundle(self.task_id, self.run_id)
        with ZipFile(bundle) as archive:
            names = archive.namelist()
            content = "".join(archive.read(name).decode("utf-8") for name in names)
        self.assertNotIn("media/source.wav", names)
        self.assertNotIn("canary-secret-123", content)
        self.assertIn("[REDACTED]", content)


if __name__ == "__main__":
    unittest.main()
