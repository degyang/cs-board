"""OpenAI API-compatible image generation adapter.

Supports ``/v1/images/generations`` and optionally ``/v1/images/edits``
when reference images are provided.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx

from csboard.domain.provider_types import (
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageModelCapabilities,
)


class OpenAIImageAdapter:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "dall-e-3",
        timeout: float = 300.0,
        max_retries: int = 3,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._key = api_key
        self._model = model
        self._timeout = timeout
        self._max_retries = max_retries

    # ── ImageModelPort ───────────────────────────────────────────────

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        if request.reference_image is not None:
            return self._generate_with_reference(request)
        return self._generate_standard(request)

    def capabilities(self) -> ImageModelCapabilities:
        return ImageModelCapabilities(
            reference_image=True,
            image_edit=True,
            supported_sizes=("1024x1024", "1536x1024", "1024x1536", "512x512"),
            supported_models=(self._model,),
        )

    # ── standard generation ──────────────────────────────────────────

    def _generate_standard(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        payload: dict[str, Any] = {
            "model": request.model or self._model,
            "prompt": request.prompt,
            "n": request.n,
            "size": f"{request.width}x{request.height}",
            "response_format": request.response_format,
        }
        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        data = self._post_json("images/generations", payload, request.timeout_seconds or self._timeout)
        images = self._extract_images(data, request.response_format)
        revised = ""
        data_list = data.get("data", [])
        if data_list and isinstance(data_list[0], dict):
            revised = str(data_list[0].get("revised_prompt", ""))
        return ImageGenerationResult(
            images=images,
            revised_prompt=revised,
            model=str(data.get("model", request.model or self._model)),
            request_id=request.request_id,
        )

    # ── reference image edit ─────────────────────────────────────────

    def _generate_with_reference(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        url = f"{self._base}/images/edits"
        headers = {"Authorization": f"Bearer {self._key}"}
        form = {
            "model": request.model or self._model,
            "prompt": request.prompt,
            "n": str(request.n),
            "size": f"{request.width}x{request.height}",
            "response_format": request.response_format,
        }
        files = {"image": ("reference.png", request.reference_image, "image/png")}

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                with httpx.Client(timeout=request.timeout_seconds or self._timeout) as client:
                    resp = client.post(url, headers=headers, data=form, files=files)
                if resp.is_error:
                    raise RuntimeError(f"Image edit API error: {resp.status_code} {resp.text[:500]}")
                data = resp.json()
                images = self._extract_images(data, request.response_format)
                return ImageGenerationResult(
                    images=images,
                    model=str(data.get("model", request.model or self._model)),
                    request_id=request.request_id,
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                if attempt < self._max_retries - 1:
                    import time
                    time.sleep(2 ** attempt * 0.5)
                    continue
                raise
        raise RuntimeError(f"Image edit failed after retries: {last_exc}")

    # ── HTTP ─────────────────────────────────────────────────────────

    def _post_json(self, endpoint: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        url = f"{self._base}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }
        for attempt in range(self._max_retries):
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(url, headers=headers, json=payload)
                if resp.is_error:
                    raise RuntimeError(f"Image API error: {resp.status_code} {resp.text[:500]}")
                return resp.json()
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt < self._max_retries - 1:
                    import time
                    time.sleep(2 ** attempt * 0.5)
                    continue
                raise
        raise RuntimeError("Image API failed after retries")  # unreachable

    # ── response extractors ──────────────────────────────────────────

    @staticmethod
    def _extract_images(data: dict[str, Any], fmt: str) -> tuple[bytes, ...]:
        images: list[bytes] = []
        for item in data.get("data", []):
            if not isinstance(item, dict):
                continue
            if fmt == "b64_json" and item.get("b64_json"):
                images.append(base64.b64decode(item["b64_json"]))
            elif item.get("url"):
                # Download from URL
                with httpx.Client(timeout=120) as client:
                    resp = client.get(item["url"])
                    resp.raise_for_status()
                    images.append(resp.content)
        return tuple(images)
