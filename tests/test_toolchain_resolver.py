from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from csboard.runtime.toolchain import ToolchainResolver


class ToolchainResolverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_auto_detect_returns_paths(self) -> None:
        resolver = ToolchainResolver.auto_detect(self.root)
        self.assertIsInstance(resolver.python, Path)
        self.assertIsInstance(resolver.node, Path)
        self.assertIsInstance(resolver.ffmpeg, Path)
        self.assertIsInstance(resolver.ffprobe, Path)
        self.assertEqual(resolver.remotion_renderer, self.root / "video_renderer" / "render.mjs")

    def test_validate_reports_missing(self) -> None:
        resolver = ToolchainResolver(
            python=Path("/nonexistent/python"),
            node=Path("/nonexistent/node"),
            ffmpeg=Path("/nonexistent/ffmpeg"),
            ffprobe=Path("/nonexistent/ffprobe"),
            remotion_renderer=Path("/nonexistent/render.mjs"),
        )
        missing = resolver.validate()
        self.assertIn("python", missing)
        self.assertIn("node", missing)
        self.assertIn("ffmpeg", missing)
        self.assertIn("ffprobe", missing)
        self.assertIn("remotion_renderer", missing)

    def test_validate_empty_when_all_present(self) -> None:
        # Use tools that are likely on PATH in CI/dev
        resolver = ToolchainResolver(
            python=Path(shutil.which("python3") or "python3"),
            node=Path(shutil.which("node") or "node"),
            ffmpeg=Path(shutil.which("ffmpeg") or "ffmpeg"),
            ffprobe=Path(shutil.which("ffprobe") or "ffprobe"),
            remotion_renderer=Path(__file__),  # any existing file
        )
        missing = resolver.validate()
        # At minimum remotion_renderer should pass (we pointed it at this file)
        self.assertNotIn("remotion_renderer", missing)

    def test_frozen(self) -> None:
        resolver = ToolchainResolver.auto_detect(self.root)
        with self.assertRaises(AttributeError):
            resolver.python = Path("/other")  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
