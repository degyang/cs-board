"""Fake media adapter — no-op operations with fixed probe results."""

from __future__ import annotations

import time
from pathlib import Path

from csboard.domain.provider_types import MediaProbeResult


class FakeMedia:
    def __init__(
        self,
        duration_ms: int = 5000,
        latency_ms: float = 0,
        should_fail: bool = False,
    ) -> None:
        self._duration_ms = duration_ms
        self._latency = latency_ms / 1000
        self._fail = should_fail
        self.call_count = 0

    def _sleep(self) -> None:
        if self._latency > 0:
            time.sleep(self._latency)

    def probe(self, path: Path) -> MediaProbeResult:
        self.call_count += 1
        self._sleep()
        if self._fail:
            raise RuntimeError("FakeMedia: injected failure")
        return MediaProbeResult(
            duration_ms=self._duration_ms,
            width=1920,
            height=1080,
            codec="h264",
            sample_rate=44100,
            channels=2,
            bitrate=5_000_000,
            format="mp4",
        )

    def normalize(self, input_path: Path, output_path: Path, target_lufs: float = -14.0) -> None:
        self.call_count += 1
        self._sleep()
        if self._fail:
            raise RuntimeError("FakeMedia: injected failure")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(input_path.read_bytes() if input_path.exists() else b"\x00")

    def concat(self, inputs: list[Path], output: Path) -> None:
        self.call_count += 1
        self._sleep()
        if self._fail:
            raise RuntimeError("FakeMedia: injected failure")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"\x00" * 128)

    def subtitle(self, video: Path, srt: Path, output: Path) -> None:
        self.call_count += 1
        self._sleep()
        if self._fail:
            raise RuntimeError("FakeMedia: injected failure")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"\x00" * 128)
