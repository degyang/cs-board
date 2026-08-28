from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from csboard.adapters.filesystem import FilesystemProjectRepository
from csboard.application.voice_units import SynthesizedVoice, VoiceUnitService
from csboard.domain.av_timing import AlignmentResult, segment_script
from csboard.domain.enums import Engine, Entrypoint, ProjectStatus, RunStatus
from csboard.domain.models import Project, Run


class FakeSynthesizer:
    def __init__(self) -> None: self.calls = 0
    def synthesize(self, unit):
        self.calls += 1
        return SynthesizedVoice(f"wav-{unit.unit_id}".encode(), 1001)


class FailingAligner:
    def align(self, unit, voice): return AlignmentResult({}, 0, 0, reason_code="ALIGNMENT_EXECUTION_FAILED")


class VoiceUnitsTest(unittest.TestCase):
    def test_reuses_voice_and_records_unit_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = FilesystemProjectRepository(Path(temporary))
            project = Project("project-1", "测试", "mountain-av-v1", Engine.WHITEBOARD, ProjectStatus.READY, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
            run = Run("run-1", "project-1", "trace-1", Entrypoint.CLI, ["command-1"], RunStatus.PENDING, "compose-video", "2026-01-01T00:00:00Z")
            repo.create_project(project); repo.create_run(run)
            synth = FakeSynthesizer(); service = VoiceUnitService(repo, synth, FailingAligner())
            units = segment_script("第一句话。第二句话。")
            manifest, timeline = service.run("project-1", "run-1", units, "test")
            service.run("project-1", "run-1", units, "test")
            self.assertEqual(synth.calls, 1)
            self.assertEqual(manifest["voices"][0]["duration_ms"], 1001)
            self.assertEqual(timeline["units"][0]["timing_source"], "equal_fallback")
            self.assertEqual(timeline["units"][0]["alignment"]["reason_code"], "ALIGNMENT_EXECUTION_FAILED")
