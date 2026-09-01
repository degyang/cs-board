"""FFmpeg MediaPort adapter — probe, normalize, concat, subtitle.

Uses ffprobe/ffmpeg CLI via subprocess.  Tool paths resolved from
:class:`csboard.runtime.toolchain.ToolchainResolver` or explicit overrides.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from csboard.domain.provider_types import MediaProbeResult


class FFmpegMediaAdapter:
    """MediaPort implementation backed by ffmpeg/ffprobe.

    Parameters
    ----------
    ffmpeg:
        Path to the ``ffmpeg`` binary.
    ffprobe:
        Path to the ``ffprobe`` binary.
    timeout:
        Default subprocess timeout in seconds.
    """

    def __init__(
        self,
        ffmpeg: Path | str = "ffmpeg",
        ffprobe: Path | str = "ffprobe",
        timeout: float = 300.0,
    ) -> None:
        self._ffmpeg = str(ffmpeg)
        self._ffprobe = str(ffprobe)
        self._timeout = timeout

    # ── MediaPort ────────────────────────────────────────────────────

    def probe(self, path: Path) -> MediaProbeResult:
        """Probe a media file using ffprobe."""
        result = self._run([
            self._ffprobe,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ])
        data = json.loads(result.stdout)

        fmt = data.get("format", {})
        duration_ms = int(round(float(fmt.get("duration", 0)) * 1000))
        bitrate = int(fmt.get("bit_rate", 0))

        video_stream: dict = {}
        audio_stream: dict = {}
        for stream in data.get("streams", []):
            codec_type = stream.get("codec_type", "")
            if codec_type == "video" and not video_stream:
                video_stream = stream
            elif codec_type == "audio" and not audio_stream:
                audio_stream = stream

        return MediaProbeResult(
            duration_ms=duration_ms,
            width=int(video_stream.get("width", 0)),
            height=int(video_stream.get("height", 0)),
            codec=str(video_stream.get("codec_name", "")),
            sample_rate=int(audio_stream.get("sample_rate", 0)),
            channels=int(audio_stream.get("channels", 0)),
            bitrate=bitrate,
            format=str(fmt.get("format_name", "")),
        )

    def normalize(self, input_path: Path, output_path: Path, target_lufs: float = -14.0) -> None:
        """Loudness-normalize an audio file using loudnorm filter."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run([
            self._ffmpeg, "-y",
            "-hide_banner", "-loglevel", "error",
            "-i", str(input_path),
            "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
            "-ar", "24000",
            "-ac", "1",
            str(output_path),
        ])

    def concat(self, inputs: list[Path], output: Path) -> None:
        """Concatenate media files using the concat demuxer."""
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            filelist = Path(f.name)
            for inp in inputs:
                f.write(f"file '{inp.resolve()}'\n")
        try:
            self._run([
                self._ffmpeg, "-y",
                "-hide_banner", "-loglevel", "error",
                "-f", "concat",
                "-safe", "0",
                "-i", str(filelist),
                "-c", "copy",
                str(output),
            ])
        finally:
            filelist.unlink(missing_ok=True)

    def mux_audio(self, video: Path, audio: Path, output: Path) -> None:
        """Mux a rendered video stream and narration audio into an MP4."""
        output.parent.mkdir(parents=True, exist_ok=True)
        self._run([
            self._ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(video), "-i", str(audio),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-shortest", "-movflags", "+faststart", str(output),
        ])

    def subtitle(self, video: Path, srt: Path, output: Path) -> None:
        """Burn subtitles into a video file."""
        output.parent.mkdir(parents=True, exist_ok=True)
        self._run([
            self._ffmpeg, "-y",
            "-hide_banner", "-loglevel", "error",
            "-i", str(video),
            "-vf", f"subtitles={srt}",
            "-c:a", "copy",
            str(output),
        ])

    # ── internal ─────────────────────────────────────────────────────

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        """Run a subprocess command with timeout and error checking."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Command timed out after {self._timeout}s: {' '.join(command[:3])}..."
            ) from exc
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Command not found: {command[0]}. "
                "Ensure ffmpeg/ffprobe are installed and on PATH."
            ) from exc

        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed (exit {result.returncode}): "
                f"{result.stderr[:500] or result.stdout[:500]}"
            )
        return result
