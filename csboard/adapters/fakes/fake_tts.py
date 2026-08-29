"""Fake TTS adapter — returns a silent WAV placeholder."""

from __future__ import annotations

import struct
import time

from csboard.domain.provider_types import TTSRequest, TTSResult


def _silent_wav(duration_ms: int = 1000, sample_rate: int = 24000) -> bytes:
    """Generate a minimal silent WAV file."""
    num_samples = int(sample_rate * duration_ms / 1000)
    # 16-bit mono PCM
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16, 1, 1,
        sample_rate,
        sample_rate * 2,
        2, 16,
        b"data",
        data_size,
    )
    return header + b"\x00" * data_size


class FakeTTS:
    def __init__(
        self,
        audio: bytes | None = None,
        duration_ms: int = 1000,
        latency_ms: float = 0,
        should_fail: bool = False,
    ) -> None:
        self._audio = audio if audio is not None else _silent_wav(duration_ms)
        self._duration_ms = duration_ms
        self._latency = latency_ms / 1000
        self._fail = should_fail
        self.call_count = 0
        self.last_request: TTSRequest | None = None

    def synthesize(self, request: TTSRequest) -> TTSResult:
        self.call_count += 1
        self.last_request = request
        if self._latency > 0:
            time.sleep(self._latency)
        if self._fail:
            raise RuntimeError("FakeTTS: injected failure")
        return TTSResult(
            audio=self._audio,
            duration_ms=self._duration_ms,
            sample_rate=request.sample_rate,
            channels=1,
            model="fake-tts",
            request_id=request.request_id,
        )
