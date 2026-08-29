"""Fake image model adapter — returns a 1×1 PNG placeholder."""

from __future__ import annotations

import base64
import time

from csboard.domain.provider_types import (
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageModelCapabilities,
)

# Minimal valid 1×1 white PNG (67 bytes)
_PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
)


class FakeImageModel:
    def __init__(
        self,
        image_bytes: bytes = _PLACEHOLDER_PNG,
        latency_ms: float = 0,
        should_fail: bool = False,
    ) -> None:
        self._image = image_bytes
        self._latency = latency_ms / 1000
        self._fail = should_fail
        self.call_count = 0
        self.last_request: ImageGenerationRequest | None = None

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        self.call_count += 1
        self.last_request = request
        if self._latency > 0:
            time.sleep(self._latency)
        if self._fail:
            raise RuntimeError("FakeImageModel: injected failure")
        return ImageGenerationResult(
            images=tuple(self._image for _ in range(request.n)),
            revised_prompt=request.prompt,
            model=request.model or "fake-image",
            request_id=request.request_id,
        )

    def capabilities(self) -> ImageModelCapabilities:
        return ImageModelCapabilities(
            reference_image=True,
            image_edit=False,
            supported_sizes=("1024x1024", "512x512"),
            supported_models=("fake-image",),
        )
