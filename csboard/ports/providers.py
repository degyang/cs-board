from __future__ import annotations

from typing import Any, Protocol


class TextModelPort(Protocol):
    def complete(self, request: dict[str, Any]) -> dict[str, Any]: ...


class ImageModelPort(Protocol):
    def generate(self, request: dict[str, Any]) -> dict[str, Any]: ...


class TextToSpeechPort(Protocol):
    def synthesize(self, request: dict[str, Any]) -> dict[str, Any]: ...


class AlignmentPort(Protocol):
    def align(self, audio_path: str, text: str) -> dict[str, Any]: ...
