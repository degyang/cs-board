"""Unit tests for FFmpegMediaAdapter.

All external calls are mocked via subprocess.run.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from csboard.adapters.ffmpeg.media_adapter import FFmpegMediaAdapter
from csboard.domain.provider_types import MediaProbeResult


def _make_ffprobe_result(
    duration: float = 5.0,
    width: int = 1920,
    height: int = 1080,
    codec: str = "h264",
    sample_rate: int = 44100,
    channels: int = 2,
    bitrate: int = 128000,
    fmt: str = "mov,mp4,m4a,3gp,3g2,mj2",
) -> MagicMock:
    """Build a mock subprocess.CompletedProcess for ffprobe output."""
    data = {
        "format": {
            "duration": str(duration),
            "bit_rate": str(bitrate),
            "format_name": fmt,
        },
        "streams": [
            {"codec_type": "video", "codec_name": codec, "width": width, "height": height},
            {"codec_type": "audio", "codec_name": "aac", "sample_rate": str(sample_rate), "channels": channels},
        ],
    }
    result = MagicMock()
    result.returncode = 0
    result.stdout = json.dumps(data)
    result.stderr = ""
    return result


def _make_success_result() -> MagicMock:
    """Build a mock subprocess.CompletedProcess for a successful ffmpeg call."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = ""
    result.stderr = ""
    return result


class TestProbe(unittest.TestCase):
    """Test FFmpegMediaAdapter.probe()."""

    @patch("subprocess.run", return_value=_make_ffprobe_result())
    def test_returns_media_probe_result(self, mock_run: MagicMock) -> None:
        adapter = FFmpegMediaAdapter()
        result = adapter.probe(Path("/tmp/test.mp4"))
        self.assertIsInstance(result, MediaProbeResult)

    @patch("subprocess.run", return_value=_make_ffprobe_result(duration=12.345))
    def test_duration_converted_to_ms(self, mock_run: MagicMock) -> None:
        adapter = FFmpegMediaAdapter()
        result = adapter.probe(Path("/tmp/test.mp4"))
        self.assertEqual(result.duration_ms, 12345)

    @patch("subprocess.run", return_value=_make_ffprobe_result(width=3840, height=2160))
    def test_resolution_parsed(self, mock_run: MagicMock) -> None:
        adapter = FFmpegMediaAdapter()
        result = adapter.probe(Path("/tmp/test.mp4"))
        self.assertEqual(result.width, 3840)
        self.assertEqual(result.height, 2160)

    @patch("subprocess.run", return_value=_make_ffprobe_result(sample_rate=48000, channels=1))
    def test_audio_fields_parsed(self, mock_run: MagicMock) -> None:
        adapter = FFmpegMediaAdapter()
        result = adapter.probe(Path("/tmp/test.wav"))
        self.assertEqual(result.sample_rate, 48000)
        self.assertEqual(result.channels, 1)

    @patch("subprocess.run", return_value=_make_ffprobe_result(bitrate=256000))
    def test_bitrate_parsed(self, mock_run: MagicMock) -> None:
        adapter = FFmpegMediaAdapter()
        result = adapter.probe(Path("/tmp/test.mp4"))
        self.assertEqual(result.bitrate, 256000)


class TestNormalize(unittest.TestCase):
    """Test FFmpegMediaAdapter.normalize()."""

    @patch("subprocess.run", return_value=_make_success_result())
    def test_calls_ffmpeg_with_loudnorm(self, mock_run: MagicMock) -> None:
        adapter = FFmpegMediaAdapter()
        adapter.normalize(Path("/tmp/in.wav"), Path("/tmp/out.wav"))
        args = mock_run.call_args[0][0]
        self.assertIn("ffmpeg", args[0])
        self.assertIn("loudnorm", " ".join(args))

    @patch("subprocess.run", return_value=_make_success_result())
    def test_custom_target_lufs(self, mock_run: MagicMock) -> None:
        adapter = FFmpegMediaAdapter()
        adapter.normalize(Path("/tmp/in.wav"), Path("/tmp/out.wav"), target_lufs=-16.0)
        args = mock_run.call_args[0][0]
        joined = " ".join(args)
        self.assertIn("I=-16.0", joined)


class TestConcat(unittest.TestCase):
    """Test FFmpegMediaAdapter.concat()."""

    @patch("subprocess.run", return_value=_make_success_result())
    def test_uses_concat_demuxer(self, mock_run: MagicMock) -> None:
        adapter = FFmpegMediaAdapter()
        adapter.concat([Path("/tmp/a.wav"), Path("/tmp/b.wav")], Path("/tmp/out.wav"))
        args = mock_run.call_args[0][0]
        self.assertIn("-f", args)
        self.assertIn("concat", args)


class TestSubtitle(unittest.TestCase):
    """Test FFmpegMediaAdapter.subtitle()."""

    @patch("subprocess.run", return_value=_make_success_result())
    def test_calls_ffmpeg_with_subtitles_filter(self, mock_run: MagicMock) -> None:
        adapter = FFmpegMediaAdapter()
        adapter.subtitle(Path("/tmp/video.mp4"), Path("/tmp/subs.srt"), Path("/tmp/out.mp4"))
        args = mock_run.call_args[0][0]
        joined = " ".join(args)
        self.assertIn("subtitles=", joined)


class TestErrorHandling(unittest.TestCase):
    """Test error handling in FFmpegMediaAdapter."""

    def test_ffprobe_failure_raises(self) -> None:
        result = MagicMock()
        result.returncode = 1
        result.stderr = "No such file or directory"
        result.stdout = ""

        adapter = FFmpegMediaAdapter()
        with patch("subprocess.run", return_value=result):
            with self.assertRaises(RuntimeError):
                adapter.probe(Path("/tmp/nonexistent.mp4"))

    def test_ffmpeg_not_found_raises(self) -> None:
        adapter = FFmpegMediaAdapter()
        with patch("subprocess.run", side_effect=FileNotFoundError("ffmpeg")):
            with self.assertRaises(RuntimeError):
                adapter.normalize(Path("/tmp/in.wav"), Path("/tmp/out.wav"))

    def test_ffmpeg_timeout_raises(self) -> None:
        import subprocess as sp
        adapter = FFmpegMediaAdapter(timeout=1.0)
        with patch("subprocess.run", side_effect=sp.TimeoutExpired("ffmpeg", 1.0)):
            with self.assertRaises(RuntimeError):
                adapter.concat([Path("/tmp/a.wav")], Path("/tmp/out.wav"))


# ── Port conformance ─────────────────────────────────────────────────

class TestFFmpegPortConformance(unittest.TestCase):
    """Verify FFmpegMediaAdapter satisfies MediaPort structurally."""

    def test_satisfies_media_port(self) -> None:
        from csboard.ports.providers import MediaPort
        adapter = FFmpegMediaAdapter()
        self.assertIsInstance(adapter, MediaPort)


if __name__ == "__main__":
    unittest.main()
