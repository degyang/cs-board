"""Tests for WhiteboardRendererAdapter."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from csboard.adapters.whiteboard.renderer_adapter import WhiteboardRendererAdapter
from csboard.domain.provider_types import RenderRequest, RenderResult, RendererCapabilities


class TestWhiteboardRendererAdapterUnit(unittest.TestCase):
    """Unit tests for WhiteboardRendererAdapter."""

    def setUp(self):
        self.adapter = WhiteboardRendererAdapter(render_script="/fake/script.py")

    def test_capabilities_returns_expected_values(self):
        caps = self.adapter.capabilities()
        self.assertIsInstance(caps, RendererCapabilities)
        self.assertIn("whiteboard", caps.engines)
        self.assertEqual(caps.max_duration_ms, 300_000)
        self.assertEqual(caps.max_resolution, (1920, 1080))

    def test_build_annotation_structure(self):
        visual = {"visual_id": "vis-1", "order": 0}
        annotation = self.adapter._build_annotation(visual, 5000)
        self.assertIn("canvas", annotation)
        self.assertIn("sequence", annotation)
        self.assertEqual(annotation["canvas"]["width"], 1920)
        self.assertEqual(annotation["canvas"]["height"], 1080)
        self.assertEqual(annotation["sceneDurationMs"], 5000)
        self.assertEqual(len(annotation["sequence"]), 1)
        self.assertEqual(annotation["sequence"][0]["id"], "vis-1")

    def test_read_json_valid(self):
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"test": "data"}, f)
            f.flush()
            result = WhiteboardRendererAdapter._read_json(Path(f.name))
            self.assertEqual(result, {"test": "data"})

    @patch("csboard.adapters.whiteboard.renderer_adapter.subprocess.run")
    def test_render_clip_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "test.png"
            image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            annotation = {"canvas": {"width": 1920, "height": 1080}, "sceneDurationMs": 5000, "sequence": []}
            output_path = Path(tmpdir) / "output.mp4"
            self.adapter._render_clip(image_path, annotation, output_path, 5000)
            mock_run.assert_called_once()

    @patch("csboard.adapters.whiteboard.renderer_adapter.subprocess.run")
    def test_render_clip_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="Error occurred", stdout="")
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "test.png"
            image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            annotation = {"canvas": {"width": 1920, "height": 1080}, "sceneDurationMs": 5000, "sequence": []}
            output_path = Path(tmpdir) / "output.mp4"
            with self.assertRaises(RuntimeError) as ctx:
                self.adapter._render_clip(image_path, annotation, output_path, 5000)
            self.assertIn("Whiteboard render failed", str(ctx.exception))


class TestWhiteboardRendererAdapterRender(unittest.TestCase):
    """Integration test for render()."""

    def setUp(self):
        self.adapter = WhiteboardRendererAdapter(render_script="/fake/script.py")

    @patch.object(WhiteboardRendererAdapter, "_render_clip")
    def test_render_success(self, mock_render_clip):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            # Create project structure
            project_dir = tmpdir / "projects" / "test-project"
            run_dir = project_dir / "runs" / "test-run"
            artifacts_dir = run_dir / "artifacts"
            output_dir = run_dir / "render"
            artifacts_dir.mkdir(parents=True)

            # Create timeline
            timeline = {
                "units": [{
                    "unit_id": "unit-1",
                    "visual_timings": [{
                        "visual_id": "vis-1",
                        "start_ms": 0,
                        "end_ms": 5000,
                    }],
                }],
            }
            (artifacts_dir / "timeline.json").write_text(json.dumps(timeline))

            # Create storyboard
            storyboard = {
                "visuals": [{
                    "visual_id": "vis-1",
                    "order": 0,
                    "prompt": "test prompt",
                }],
            }
            (artifacts_dir / "storyboard.json").write_text(json.dumps(storyboard))

            # Create illustration manifest
            illustration_manifest = {
                "illustrations": [{
                    "visual_id": "vis-1",
                    "image_path": "images/vis-1.png",
                }],
            }
            (artifacts_dir / "illustration-manifest.json").write_text(json.dumps(illustration_manifest))

            # Create image file
            images_dir = project_dir / "images"
            images_dir.mkdir(parents=True)
            (images_dir / "vis-1.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

            # Create render request
            request = RenderRequest(
                timeline_path=artifacts_dir / "timeline.json",
                storyboard_path=artifacts_dir / "storyboard.json",
                illustration_manifest_path=artifacts_dir / "illustration-manifest.json",
                output_dir=output_dir,
                request_id="test-render",
            )

            # Mock the render_clip to create output
            def fake_render_clip(image_path, annotation, output_path, duration_ms):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(b"\x00" * 128)
            mock_render_clip.side_effect = fake_render_clip

            # Execute render
            result = self.adapter.render(request)

            # Verify result
            self.assertIsInstance(result, RenderResult)
            self.assertEqual(result.duration_ms, 5000)
            self.assertGreater(result.frames, 0)
            self.assertEqual(result.request_id, "test-render")
            self.assertIn("clips", result.provider_metadata)
            self.assertEqual(len(result.provider_metadata["clips"]), 1)


if __name__ == "__main__":
    unittest.main()
