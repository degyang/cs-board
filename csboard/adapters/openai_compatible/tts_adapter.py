"""Provider-neutral OpenAI-compatible speech synthesis adapter."""

from __future__ import annotations

import base64
import binascii
from typing import Any

import httpx

from csboard.domain.provider_types import TTSRequest, TTSResult


def preset_voice_profiles(service: Any) -> list[dict[str, Any]]:
    """Provider metadata for MiMo presets, kept out of domain/application."""
    model = str(service.model or "").split(",", 1)[0].strip()
    if service.adapter_type != "openai_compatible" or model != "mimo-v2.5-tts":
        return []
    voices = (
        ("bingtang", "冰糖", "zh-CN", "female"),
        ("moli", "茉莉", "zh-CN", "female"),
        ("soda", "苏打", "zh-CN", "male"),
        ("baihua", "白桦", "zh-CN", "male"),
        ("mia", "Mia", "en-US", "female"),
        ("chloe", "Chloe", "en-US", "female"),
        ("milo", "Milo", "en-US", "male"),
        ("dean", "Dean", "en-US", "male"),
    )
    return [
        {
            "profile_id": f"{service.service_id}-{profile_suffix}",
            "name": voice_id,
            "kind": "provider-preset",
            "remote_voice_id": voice_id,
            "model_id": model,
            "language": language, "gender": gender,
            "vendor_id": "mimo", "vendor_name": "MiMo",
            "tags": ["preset"],
        }
        for profile_suffix, voice_id, language, gender in voices
    ]


class OpenAITTSAdapter:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 60.0) -> None:
        self._base = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model.split(",", 1)[0].strip()
        self._timeout = timeout

    def synthesize(self, request: TTSRequest) -> TTSResult:
        style = request.voice_config.get("instruction", "")
        audio: dict[str, str] = {"format": str(request.voice_config.get("format", "wav"))}
        if request.voice_id:
            audio["voice"] = request.voice_id
        payload = {"model": self._model, "audio": audio, "messages": [
            {"role": "user", "content": style or "Speak naturally."},
            {"role": "assistant", "content": request.text},
        ]}
        try:
            response = httpx.post(f"{self._base}/chat/completions", headers={"Authorization": f"Bearer {self._api_key}"}, json=payload, timeout=request.timeout_seconds or self._timeout)
            response.raise_for_status()
            body: dict[str, Any] = response.json()
            encoded = body.get("audio") or body.get("audio_base64")
            if not encoded and isinstance(body.get("choices"), list) and body["choices"]:
                encoded = body["choices"][0].get("message", {}).get("audio", {}).get("data")
            if not isinstance(encoded, str):
                raise RuntimeError("TTS_RESPONSE_MISSING_AUDIO")
            return TTSResult(audio=base64.b64decode(encoded, validate=True), model=self._model,
                             sample_rate=request.sample_rate, request_id=str(response.headers.get("x-request-id", request.request_id)))
        except Exception as exc:
            raise RuntimeError("TTS_PROVIDER_REQUEST_FAILED") from exc
