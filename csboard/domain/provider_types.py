"""Typed request/result dataclasses for provider ports.

These replace the untyped ``dict[str, Any]`` signatures in the original
port definitions.  Domain logic and stages depend only on these types,
never on HTTP payload shapes or SDK objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Text generation ──────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class TextGenerationRequest:
    messages: list[dict[str, str]]
    model: str = ""
    json_schema: dict[str, Any] | None = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: float = 60.0
    request_id: str = ""


@dataclass(frozen=True, slots=True)
class TextGenerationResult:
    text: str
    structured_value: Any = None
    finish_reason: str = "stop"
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    request_id: str = ""
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TextModelCapabilities:
    json_schema: bool = False
    model_discovery: bool = False
    max_context_tokens: int = 0
    supported_models: tuple[str, ...] = ()


# ── Image generation ─────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ImageGenerationRequest:
    prompt: str
    model: str = ""
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    n: int = 1
    response_format: str = "b64_json"
    reference_image: bytes | None = None
    timeout_seconds: float = 120.0
    request_id: str = ""


@dataclass(frozen=True, slots=True)
class ImageGenerationResult:
    images: tuple[bytes, ...]
    revised_prompt: str = ""
    model: str = ""
    request_id: str = ""
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ImageModelCapabilities:
    reference_image: bool = False
    image_edit: bool = False
    supported_sizes: tuple[str, ...] = ()
    supported_models: tuple[str, ...] = ()


# ── Text-to-speech ───────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class TTSRequest:
    text: str
    voice_id: str = ""
    reference_audio: Path | None = None
    language: str = "zh"
    sample_rate: int = 24000
    timeout_seconds: float = 60.0
    request_id: str = ""


@dataclass(frozen=True, slots=True)
class TTSResult:
    audio: bytes
    duration_ms: int = 0
    sample_rate: int = 24000
    channels: int = 1
    model: str = ""
    request_id: str = ""
    provider_metadata: dict[str, Any] = field(default_factory=dict)


# ── Alignment (Whisper) ──────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class AlignmentRequest:
    audio_path: Path
    text: str
    language: str = "zh"
    timeout_seconds: float = 60.0
    request_id: str = ""


@dataclass(frozen=True, slots=True)
class AlignmentResult:
    starts_ms: dict[str, int]
    coverage: float = 0.0
    confidence: float = 0.0
    engine: str = "whisper"
    reason_code: str | None = None
    request_id: str = ""


# ── Rendering ────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class RenderRequest:
    timeline_path: Path
    storyboard_path: Path
    illustration_manifest_path: Path
    output_dir: Path
    engine: str = "whiteboard"
    timeout_seconds: float = 600.0
    request_id: str = ""


@dataclass(frozen=True, slots=True)
class RenderResult:
    output_path: Path
    duration_ms: int = 0
    frames: int = 0
    request_id: str = ""
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RendererCapabilities:
    engines: tuple[str, ...] = ("whiteboard",)
    max_duration_ms: int = 0
    max_resolution: tuple[int, int] = (1920, 1080)


# ── Media operations ─────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class MediaProbeResult:
    duration_ms: int = 0
    width: int = 0
    height: int = 0
    codec: str = ""
    sample_rate: int = 0
    channels: int = 0
    bitrate: int = 0
    format: str = ""
