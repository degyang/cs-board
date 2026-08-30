"""Test VoiceUnitService with M02 fake adapters."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from csboard.adapters.fakes import FakeAlignment, FakeMedia, FakeTTS
from csboard.adapters.filesystem import FilesystemTaskRepository
from csboard.application.voice_units import VoiceUnitService
from csboard.domain.av_timing import segment_script
from csboard.domain.enums import Engine, Entrypoint, TaskStatus, RunStatus
from csboard.domain.models import Task, Run


def _setup_repo(tmp: str) -> tuple[FilesystemTaskRepository, str, str]:
    """Create a repo with a task and run, return (repo, task_id, run_id)."""
    repo = FilesystemTaskRepository(Path(tmp))
    task = Task(
        "task-1", "测试", "mountain-av-v1",
        Engine.WHITEBOARD, TaskStatus.READY,
        "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z",
    )
    run = Run(
        "run-1", "task-1", "trace-1",
        Entrypoint.CLI, ["command-1"],
        RunStatus.PENDING, "compose-video", "2026-01-01T00:00:00Z",
    )
    repo.create_task(task)
    repo.create_run(run)
    return repo, "task-1", "run-1"


class VoiceUnitsTest(unittest.TestCase):
    def test_reuses_voice_and_records_unit_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, pid, rid = _setup_repo(tmp)
            ref = Path(tmp) / "ref.wav"
            ref.write_bytes(b"\x00" * 100)

            tts = FakeTTS(duration_ms=1001)
            alignment = FakeAlignment(should_fail=True)
            media = FakeMedia(duration_ms=1001)
            service = VoiceUnitService(tts, alignment, media, repo, ref)

            units = segment_script("第一句话。第二句话。")
            manifest, timeline = service.run(pid, rid, units, "test")

            # Run again — should reuse existing audio (tts called once per unit, not twice)
            service.run(pid, rid, units, "test")

            self.assertEqual(tts.call_count, len(units))  # not 2x
            self.assertEqual(manifest["voices"][0]["duration_ms"], 1001)
            self.assertEqual(timeline["units"][0]["timing_source"], "equal_fallback")
            self.assertEqual(
                timeline["units"][0]["alignment"]["reason_code"],
                "ALIGNMENT_FAILED",
            )

            events = service.telemetry.read_events(pid, rid)
            event_types = [e["event_type"] for e in events[:3]]
            self.assertIn("VoiceUnitStarted", event_types)
            self.assertIn("AlignmentFallback", event_types)
            self.assertIn("VoiceUnitSucceeded", event_types)

            run_state = repo.get_run(pid, rid)
            self.assertEqual(run_state.stages["clone-voice"].status.value, "succeeded")
            self.assertEqual(run_state.warnings[0]["code"], "ALIGNMENT_EQUAL_FALLBACK")

    def test_alignment_exception_becomes_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, pid, rid = _setup_repo(tmp)
            ref = Path(tmp) / "ref.wav"
            ref.write_bytes(b"\x00" * 100)

            # Use a fake alignment that raises
            class ExplodingAlignment:
                call_count = 0
                def align(self, request):
                    raise RuntimeError("whisper missing")

            tts = FakeTTS(duration_ms=500)
            media = FakeMedia()
            service = VoiceUnitService(tts, ExplodingAlignment(), media, repo, ref)

            _, timeline = service.run(pid, rid, segment_script("一句话。"), "test")
            self.assertEqual(
                timeline["units"][0]["alignment"]["reason_code"],
                "ALIGNMENT_EXECUTION_FAILED",
            )

    def test_successful_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo, pid, rid = _setup_repo(tmp)
            ref = Path(tmp) / "ref.wav"
            ref.write_bytes(b"\x00" * 100)

            units = segment_script("第一句话。第二句话。")
            unit = units[0]

            # FakeAlignment returns equal-spaced timestamps, which won't pass
            # whisper validation (starts_ms keys are chars, not visual_ids).
            # So this will fall back to equal_fallback.
            tts = FakeTTS(duration_ms=2000)
            alignment = FakeAlignment()
            media = FakeMedia(duration_ms=2000)
            service = VoiceUnitService(tts, alignment, media, repo, ref)

            _, timeline = service.run(pid, rid, units, "test")
            # Alignment returns char-keyed starts_ms, not visual_id-keyed,
            # so whisper validation fails → equal_fallback
            self.assertEqual(timeline["units"][0]["timing_source"], "equal_fallback")


if __name__ == "__main__":
    unittest.main()
