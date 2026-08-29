"""Fake renderer adapter — writes a placeholder file."""

from __future__ import annotations

import time
from pathlib import Path

from csboard.domain.provider_types import (
    RenderRequest,
    RenderResult,
    RendererCapabilities,
)


class FakeRenderer:
    def __init__(
        self,
        latency_ms: float = 0,
        should_fail: bool = False,
    ) -> None:
        self._latency = latency_ms / 1000
        self._fail = should_fail
        self.call_count = 0
        self.last_request: RenderRequest | None = None

    def render(self, request: RenderRequest) -> RenderResult:
        self.call_count += 1
        self.last_request = request
        if self._latency > 0:
            time.sleep(self._latency)
        if self._fail:
            raise RuntimeError("FakeRenderer: injected failure")
        output = request.output_dir / "render_output.mp4"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"\x00" * 128)  # placeholder
        return RenderResult(
            output_path=output,
            duration_ms=5000,
            frames=150,
            request_id=request.request_id,
        )

    def capabilities(self) -> RendererCapabilities:
        return RendererCapabilities(
            engines=("whiteboard",),
            max_duration_ms=300_000,
            max_resolution=(1920, 1080),
        )
