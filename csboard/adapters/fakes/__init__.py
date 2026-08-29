"""Fake (in-memory) adapters for testing and local development.

Every fake accepts ``latency_ms`` and ``should_fail`` to simulate
real-world behaviour without network calls.
"""

from csboard.adapters.fakes.fake_alignment import FakeAlignment
from csboard.adapters.fakes.fake_image_model import FakeImageModel
from csboard.adapters.fakes.fake_media import FakeMedia
from csboard.adapters.fakes.fake_renderer import FakeRenderer
from csboard.adapters.fakes.fake_text_model import FakeTextModel
from csboard.adapters.fakes.fake_tts import FakeTTS

__all__ = [
    "FakeAlignment",
    "FakeImageModel",
    "FakeMedia",
    "FakeRenderer",
    "FakeTextModel",
    "FakeTTS",
]
