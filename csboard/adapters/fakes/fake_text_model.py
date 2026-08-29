"""Fake text model adapter — returns deterministic responses."""

from __future__ import annotations

import time

from csboard.domain.provider_types import (
    TextGenerationRequest,
    TextGenerationResult,
    TextModelCapabilities,
)


class FakeTextModel:
    def __init__(
        self,
        response_text: str = '{"result": "ok"}',
        latency_ms: float = 0,
        should_fail: bool = False,
    ) -> None:
        self._text = response_text
        self._latency = latency_ms / 1000
        self._fail = should_fail
        self.call_count = 0
        self.last_request: TextGenerationRequest | None = None

    def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        self.call_count += 1
        self.last_request = request
        if self._latency > 0:
            time.sleep(self._latency)
        if self._fail:
            raise RuntimeError("FakeTextModel: injected failure")
        return TextGenerationResult(
            text=self._text,
            finish_reason="stop",
            input_tokens=len(request.messages) * 10,
            output_tokens=len(self._text),
            model=request.model or "fake-text",
            request_id=request.request_id,
        )

    def capabilities(self) -> TextModelCapabilities:
        return TextModelCapabilities(
            json_schema=True,
            model_discovery=True,
            max_context_tokens=128000,
            supported_models=("fake-text",),
        )
