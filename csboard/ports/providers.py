"""Provider port protocols — the contracts stages depend on.

All request/result types live in :mod:`csboard.domain.provider_types`.
Adapters implement these protocols; stages consume them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from csboard.domain.provider_types import (
    AlignmentRequest,
    AlignmentResult,
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageModelCapabilities,
    MediaProbeResult,
    RenderRequest,
    RenderResult,
    RendererCapabilities,
    TextGenerationRequest,
    TextGenerationResult,
    TextModelCapabilities,
    TTSRequest,
    TTSResult,
)


@runtime_checkable
class TextModelPort(Protocol):
    def generate(self, request: TextGenerationRequest) -> TextGenerationResult: ...
    def capabilities(self) -> TextModelCapabilities: ...


@runtime_checkable
class ImageModelPort(Protocol):
    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult: ...
    def capabilities(self) -> ImageModelCapabilities: ...


@runtime_checkable
class TextToSpeechPort(Protocol):
    def synthesize(self, request: TTSRequest) -> TTSResult: ...


@runtime_checkable
class AlignmentPort(Protocol):
    def align(self, request: AlignmentRequest) -> AlignmentResult: ...


@runtime_checkable
class RendererPort(Protocol):
    def render(self, request: RenderRequest) -> RenderResult: ...
    def capabilities(self) -> RendererCapabilities: ...


@runtime_checkable
class MediaPort(Protocol):
    def probe(self, path: Path) -> MediaProbeResult: ...
    def normalize(self, input_path: Path, output_path: Path, target_lufs: float = -14.0) -> None: ...
    def concat(self, inputs: list[Path], output: Path) -> None: ...
    def subtitle(self, video: Path, srt: Path, output: Path) -> None: ...
