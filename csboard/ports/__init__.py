"""Stable interfaces used by the shared application core."""
from csboard.ports.providers import AlignmentPort, ImageModelPort, TextModelPort, TextToSpeechPort

__all__ = ["AlignmentPort", "ImageModelPort", "TextModelPort", "TextToSpeechPort"]
