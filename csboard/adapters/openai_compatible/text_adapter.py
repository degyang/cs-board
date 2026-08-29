"""OpenAI API-compatible text generation adapter.

Supports both ``/v1/chat/completions`` and ``/v1/responses`` protocols.
"""

from __future__ import annotations

from typing import Any

import httpx

from csboard.domain.provider_types import (
    TextGenerationRequest,
    TextGenerationResult,
    TextModelCapabilities,
)


class OpenAITextAdapter:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "gpt-4o",
        protocol: str = "chat_completions",
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._key = api_key
        self._model = model
        self._protocol = protocol
        self._timeout = timeout
        self._max_retries = max_retries

    # ── TextModelPort ────────────────────────────────────────────────

    def generate(self, request: TextGenerationRequest) -> TextGenerationResult:
        model = request.model or self._model
        if self._protocol == "responses":
            payload = self._responses_payload(request, model)
            endpoint = "responses"
        else:
            payload = self._chat_payload(request, model)
            endpoint = "chat/completions"

        data = self._post(endpoint, payload, request.timeout_seconds or self._timeout)

        text = self._extract_text(data)
        usage = data.get("usage", {})
        return TextGenerationResult(
            text=text,
            finish_reason=self._extract_finish(data),
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            model=str(data.get("model", model)),
            request_id=request.request_id,
            provider_metadata={"raw": data} if not text else {},
        )

    def capabilities(self) -> TextModelCapabilities:
        return TextModelCapabilities(
            json_schema=True,
            model_discovery=True,
            max_context_tokens=128000,
            supported_models=(self._model,),
        )

    # ── request builders ─────────────────────────────────────────────

    def _chat_payload(self, req: TextGenerationRequest, model: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": req.messages,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        }
        if req.json_schema:
            body["response_format"] = {"type": "json_schema", "json_schema": req.json_schema}
        return body

    def _responses_payload(self, req: TextGenerationRequest, model: str) -> dict[str, Any]:
        # Flatten messages into a single input string for Responses API
        parts = []
        for msg in req.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"[{role}]\n{content}")
        body: dict[str, Any] = {
            "model": model,
            "input": "\n\n".join(parts),
        }
        if req.json_schema:
            body["text"] = {"format": {"type": "json_schema", "json_schema": req.json_schema}}
        return body

    # ── HTTP ─────────────────────────────────────────────────────────

    def _post(self, endpoint: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        url = f"{self._base}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(url, headers=headers, json=payload)
                if resp.is_error:
                    raise RuntimeError(
                        f"OpenAI-compatible API error: {resp.status_code} {resp.text[:500]}"
                    )
                return resp.json()
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                if attempt < self._max_retries - 1:
                    import time
                    time.sleep(2 ** attempt * 0.5)
                    continue
                raise
        raise RuntimeError(f"OpenAI-compatible API failed after retries: {last_exc}")

    # ── response extractors ──────────────────────────────────────────

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        # Chat Completions
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {})
            content = msg.get("content")
            if content:
                return str(content)
        # Responses API
        output = data.get("output")
        if isinstance(output, list):
            for block in output:
                if isinstance(block, dict):
                    content = block.get("content")
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "output_text":
                                return str(item.get("text", ""))
                    elif isinstance(content, str):
                        return content
        return ""

    @staticmethod
    def _extract_finish(data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            return str(choices[0].get("finish_reason", "stop"))
        return "stop"
