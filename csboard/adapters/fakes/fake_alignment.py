"""Fake alignment adapter — returns equal-spaced timestamps."""

from __future__ import annotations

import time

from csboard.domain.provider_types import AlignmentRequest, AlignmentResult


class FakeAlignment:
    def __init__(
        self,
        latency_ms: float = 0,
        should_fail: bool = False,
    ) -> None:
        self._latency = latency_ms / 1000
        self._fail = should_fail
        self.call_count = 0
        self.last_request: AlignmentRequest | None = None

    def align(self, request: AlignmentRequest) -> AlignmentResult:
        self.call_count += 1
        self.last_request = request
        if self._latency > 0:
            time.sleep(self._latency)
        if self._fail:
            return AlignmentResult(
                starts_ms={},
                coverage=0.0,
                confidence=0.0,
                engine="fake-whisper",
                reason_code="ALIGNMENT_FAILED",
            )
        # Equal-spaced timestamps for each character
        char_count = len(request.text)
        starts: dict[str, int] = {}
        for i, ch in enumerate(request.text):
            starts[ch] = int(i * 5000 / max(char_count, 1))
        return AlignmentResult(
            starts_ms=starts,
            coverage=1.0,
            confidence=0.95,
            engine="fake-whisper",
        )
