"""Tests for CompositionService."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from csboard.adapters.fakes import FakeMedia
from csboard.adapters.ffmpeg.media_adapter import FFmpegMediaAdapter
from csboard.adapters.filesystem import FilesystemArtifactStore, FilesystemTaskRepository
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.composition import CompositionService
from csboard.domain.enums import Entrypoint, TaskStatus, RunStatus
from csboard.domain.models import Task, Run


class TestCompositionServiceUnit(unittest.TestCase):
    """Unit tests for CompositionService."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.repo = FilesystemTaskRepository(self.tmpdir)
        self.media = FakeMedia()

        # Create project and run
        self.task = Task(
            task_id="proj-comp",
            title="Composition Test",
            pipeline_id="mountain-av-v1",
            engine="whiteboard",
            status=TaskStatus.READY,
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            active_run_id="run-comp",
        )
        self.run = Run(
            run_id="run-comp",
            task_id="proj-comp",
            trace_id="trace-comp",
            entrypoint=Entrypoint.CLI,
            command_ids=["cmd-1"],
            status=RunStatus.RUNNING,
            target_stage="compose-video",
            started_at="2025-01-01T00:00:00Z",
        )
        self.repo.create_task(self.task)
        self.repo.create_run(self.run)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_artifacts(self):
        """Create required artifacts for composition."""
        run_dir = self.repo.run_dir("proj-comp", "run-comp")
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Create render manifest
        render_manifest = {
            "generated_at": "2025-01-01T00:00:00Z",
            "engine": "whiteboard",
            "total_duration_ms": 10000,
            "total_frames": 300,
            "clips": [
                {
                    "visual_id": "vis-1",
                    "unit_id": "unit-1",
                    "clip_path": "render/clips/vis-1.mp4",
                    "duration_ms": 5000,
                    "start_ms": 0,
                    "end_ms": 5000,
                },
                {
                    "visual_id": "vis-2",
                    "unit_id": "unit-2",
                    "clip_path": "render/clips/vis-2.mp4",
                    "duration_ms": 5000,
                    "start_ms": 5000,
                    "end_ms": 10000,
                },
            ],
            "output_path": "projects/proj-comp/runs/run-comp/render/silent_master.mp4",
        }
        (artifacts_dir / "render-manifest.json").write_text(
            json.dumps(render_manifest), encoding="utf-8"
        )

        # Create voice manifest
        voice_manifest = {
            "generated_at": "2025-01-01T00:00:00Z",
            "provider": "FakeTTS",
            "total_duration_ms": 10000,
            "unit_count": 2,
            "voices": [
                {
                    "unit_id": "unit-1",
                    "audio_path": "artifacts/media/voices/unit-1.wav",
                    "duration_ms": 5000,
                },
                {
                    "unit_id": "unit-2",
                    "audio_path": "artifacts/media/voices/unit-2.wav",
                    "duration_ms": 5000,
                },
            ],
        }
        (artifacts_dir / "voice-manifest.json").write_text(
            json.dumps(voice_manifest), encoding="utf-8"
        )

        # Create timeline
        timeline = {
            "generated_at": "2025-01-01T00:00:00Z",
            "total_duration_ms": 10000,
            "units": [
                {
                    "unit_id": "unit-1",
                    "text": "Hello world",
                    "start_ms": 0,
                    "end_ms": 5000,
                },
                {
                    "unit_id": "unit-2",
                    "text": "This is a test",
                    "start_ms": 5000,
                    "end_ms": 10000,
                },
            ],
        }
        (artifacts_dir / "timeline.json").write_text(
            json.dumps(timeline), encoding="utf-8"
        )

        # Create clip files
        clips_dir = run_dir / "render" / "clips"
        clips_dir.mkdir(parents=True)
        (clips_dir / "vis-1.mp4").write_bytes(b"\x00" * 128)
        (clips_dir / "vis-2.mp4").write_bytes(b"\x00" * 128)

        voices_dir = artifacts_dir / "media" / "voices"
        voices_dir.mkdir(parents=True)
        (voices_dir / "unit-1.wav").write_bytes(b"\x00" * 128)
        (voices_dir / "unit-2.wav").write_bytes(b"\x00" * 128)
        store = FilesystemArtifactStore(self.repo)
        store.commit_bytes("proj-comp", "run-comp", "render.manifest", "render/render-manifest.json", (artifacts_dir / "render-manifest.json").read_bytes(), "render-visuals")
        store.commit_bytes("proj-comp", "run-comp", "audio.voice-manifest", "audio/voice-manifest.json", (artifacts_dir / "voice-manifest.json").read_bytes(), "clone-voice")
        store.commit_bytes("proj-comp", "run-comp", "timing.timeline", "timing/timeline.json", (artifacts_dir / "timeline.json").read_bytes(), "clone-voice")

        return artifacts_dir

    def test_compose_video_success(self):
        """Test successful video composition."""
        self._create_artifacts()
        service = CompositionService(self.media, self.repo)
        result = service.run("proj-comp", "run-comp")

        self.assertIn("artifact_key", result)
        self.assertEqual(result["artifact_key"], "output.final-manifest")
        self.assertIn("output_path", result)
        self.assertIn("duration_ms", result)
        self.assertEqual(result["duration_ms"], 10000)
        self.assertEqual(result["visual_count"], 2)
        self.assertEqual(result["unit_count"], 2)

    def test_compose_video_creates_output(self):
        """Test that composition creates output files."""
        self._create_artifacts()
        service = CompositionService(self.media, self.repo)
        result = service.run("proj-comp", "run-comp")

        # Check output file exists
        output_path = Path(result["output_path"])
        self.assertTrue(output_path.exists())

    def test_compose_video_creates_subtitle(self):
        """Test that composition creates subtitle file."""
        self._create_artifacts()
        service = CompositionService(self.media, self.repo)
        result = service.run("proj-comp", "run-comp")

        # Check subtitle file exists
        run_dir = self.repo.run_dir("proj-comp", "run-comp")
        subtitle_path = run_dir / "artifacts" / "subtitles.srt"
        self.assertTrue(subtitle_path.exists())
        content = subtitle_path.read_text(encoding="utf-8")
        self.assertIn("Hello world", content)
        self.assertIn("This is a test", content)

    def test_compose_video_final_manifest(self):
        """Test that final manifest is created and has correct structure."""
        self._create_artifacts()
        service = CompositionService(self.media, self.repo)
        service.run("proj-comp", "run-comp")

        # Read final manifest
        run_dir = self.repo.run_dir("proj-comp", "run-comp")
        manifest_path = run_dir / "artifacts" / "output" / "final-manifest.json"
        self.assertTrue(manifest_path.exists())

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertIn("generated_at", manifest)
        self.assertIn("output", manifest)
        self.assertIn("clips", manifest)
        self.assertIn("audio_units", manifest)
        self.assertIn("quality", manifest)

        # Check quality section
        quality = manifest["quality"]
        self.assertEqual(quality["clip_count"], 2)
        self.assertEqual(quality["unit_count"], 2)
        self.assertEqual(quality["total_duration_ms"], 10000)
        self.assertTrue(quality["has_subtitles"])

    def test_format_srt_time(self):
        """Test SRT time formatting."""
        self.assertEqual(CompositionService._format_srt_time(0), "00:00:00,000")
        self.assertEqual(CompositionService._format_srt_time(1500), "00:00:01,500")
        self.assertEqual(CompositionService._format_srt_time(61000), "00:01:01,000")
        self.assertEqual(CompositionService._format_srt_time(3661000), "01:01:01,000")


class TestCompositionServiceIntegration(unittest.TestCase):
    """Integration test with FakeMedia."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.repo = FilesystemTaskRepository(self.tmpdir)
        self.media = FakeMedia()

        # Create project and run
        self.task = Task(
            task_id="proj-int",
            title="Integration Test",
            pipeline_id="mountain-av-v1",
            engine="whiteboard",
            status=TaskStatus.READY,
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            active_run_id="run-int",
        )
        self.run = Run(
            run_id="run-int",
            task_id="proj-int",
            trace_id="trace-int",
            entrypoint=Entrypoint.CLI,
            command_ids=["cmd-1"],
            status=RunStatus.RUNNING,
            target_stage="compose-video",
            started_at="2025-01-01T00:00:00Z",
        )
        self.repo.create_task(self.task)
        self.repo.create_run(self.run)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_full_composition_flow(self):
        """Test complete composition flow with all artifacts."""
        run_dir = self.repo.run_dir("proj-int", "run-int")
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Create all required artifacts
        render_manifest = {
            "total_duration_ms": 5000,
            "clips": [{
                "visual_id": "vis-1",
                "unit_id": "unit-1",
                "clip_path": "render/clips/vis-1.mp4",
                "duration_ms": 5000,
            }],
        }
        (artifacts_dir / "render-manifest.json").write_text(json.dumps(render_manifest))

        voice_manifest = {
            "voices": [{
                "unit_id": "unit-1",
                "audio_path": "artifacts/media/voices/unit-1.wav",
                "duration_ms": 5000,
            }],
        }
        (artifacts_dir / "voice-manifest.json").write_text(json.dumps(voice_manifest))

        timeline = {
            "units": [{
                "unit_id": "unit-1",
                "text": "Test subtitle",
                "start_ms": 0,
                "end_ms": 5000,
            }],
        }
        (artifacts_dir / "timeline.json").write_text(json.dumps(timeline))

        # Create clip file
        clips_dir = run_dir / "render" / "clips"
        clips_dir.mkdir(parents=True)
        (clips_dir / "vis-1.mp4").write_bytes(b"\x00" * 128)
        voices_dir = artifacts_dir / "media" / "voices"
        voices_dir.mkdir(parents=True)
        (voices_dir / "unit-1.wav").write_bytes(b"\x00" * 128)
        store = FilesystemArtifactStore(self.repo)
        store.commit_bytes("proj-int", "run-int", "render.manifest", "render/render-manifest.json", (artifacts_dir / "render-manifest.json").read_bytes(), "render-visuals")
        store.commit_bytes("proj-int", "run-int", "audio.voice-manifest", "audio/voice-manifest.json", (artifacts_dir / "voice-manifest.json").read_bytes(), "clone-voice")
        store.commit_bytes("proj-int", "run-int", "timing.timeline", "timing/timeline.json", (artifacts_dir / "timeline.json").read_bytes(), "clone-voice")

        # Run composition
        service = CompositionService(self.media, self.repo)
        result = service.run("proj-int", "run-int")

        # Verify
        self.assertTrue(result["output_path"])
        self.assertEqual(result["duration_ms"], 5000)
        self.assertEqual(result["visual_count"], 1)
        self.assertEqual(result["unit_count"], 1)

        # Verify final manifest
        manifest_path = artifacts_dir / "output" / "final-manifest.json"
        self.assertTrue(manifest_path.exists())

        # Verify subtitle
        subtitle_path = artifacts_dir / "subtitles.srt"
        self.assertTrue(subtitle_path.exists())
        content = subtitle_path.read_text(encoding="utf-8")
        self.assertIn("Test subtitle", content)


class TestCompositionServiceFFmpegAcceptance(unittest.TestCase):
    """A real-media guard: placeholders must never satisfy composition."""

    def test_real_ffmpeg_produces_playable_audio_video(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = FilesystemTaskRepository(root)
            task = Task("proj-real", "real", "mountain-av-v1", "whiteboard", TaskStatus.READY,
                              "2025-01-01T00:00:00Z", "2025-01-01T00:00:00Z", "run-real")
            run = Run("run-real", "proj-real", "trace-real", Entrypoint.CLI, ["cmd-real"], RunStatus.RUNNING,
                      "compose-video", "2025-01-01T00:00:00Z")
            repo.create_task(task)
            repo.create_run(run)
            run_dir = repo.run_dir("proj-real", "run-real")
            clip = run_dir / "render" / "clips" / "v-01.mp4"
            wav = run_dir / "artifacts" / "media" / "voices" / "u-01.wav"
            clip.parent.mkdir(parents=True)
            wav.parent.mkdir(parents=True)
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x180:d=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)], check=True, capture_output=True)
            subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-ar", "24000", "-ac", "1", str(wav)], check=True, capture_output=True)
            store = FilesystemArtifactStore(repo)
            store.commit_bytes("proj-real", "run-real", "render.manifest", "render/render-manifest.json", json.dumps({"total_duration_ms": 1000, "clips": [{"visual_id": "v-01", "unit_id": "u-01", "clip_path": "render/clips/v-01.mp4", "duration_ms": 1000}]}).encode(), "render-visuals")
            store.commit_bytes("proj-real", "run-real", "audio.voice-manifest", "audio/voice-manifest.json", json.dumps({"voices": [{"unit_id": "u-01", "audio_path": "artifacts/media/voices/u-01.wav", "duration_ms": 1000}]}).encode(), "clone-voice")
            store.commit_bytes("proj-real", "run-real", "timing.timeline", "timing/timeline.json", json.dumps({"units": [{"unit_id": "u-01", "duration_ms": 1000}]}).encode(), "clone-voice")
            store.commit_bytes("proj-real", "run-real", "planning.av-plan", "planning/av-plan.json", json.dumps({"voice_units": [{"unit_id": "u-01", "text": "验收字幕"}]}).encode(), "segment-script")

            result = CompositionService(FFmpegMediaAdapter(), repo).run("proj-real", "run-real")
            probe = FFmpegMediaAdapter().probe(Path(result["output_path"]))
            self.assertGreater(probe.duration_ms, 0)
            self.assertEqual(probe.codec, "h264")
            self.assertGreater(probe.sample_rate, 0)


if __name__ == "__main__":
    unittest.main()
