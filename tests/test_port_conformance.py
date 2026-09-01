"""Port conformance tests — verify adapters satisfy their Protocol contracts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from csboard.adapters.fakes import FakeAlignment, FakeImageModel, FakeMedia, FakeTextModel, FakeTTS
from csboard.ports.providers import (
    AlignmentPort,
    ImageModelPort,
    MediaPort,
    RendererPort,
    TextModelPort,
    TextToSpeechPort,
)


def _check_protocol(instance, protocol_cls, *, exclude: frozenset[str] = frozenset()):
    """Return the set of required methods that *instance* does NOT implement."""
    # Filter out internal Protocol attributes
    protocol_attrs = {
        '_is_protocol', '_abc_impl', '__module__', '__weakref__', '__annotations__',
        '__non_callable_proto_members__', '__parameters__', '__dict__', '_is_runtime_protocol',
        '__doc__', '__protocol_attrs__', '__abstractmethods__',
    }
    required = frozenset(vars(protocol_cls).keys()) - protocol_attrs - exclude
    missing = set()
    for name in required:
        if not callable(getattr(instance, name, None)):
            missing.add(name)
    return missing


class FakeAdapterConformance(unittest.TestCase):
    """Verify all fake adapters satisfy their Protocol."""

    def test_fake_text_model(self):
        missing = _check_protocol(FakeTextModel(), TextModelPort)
        self.assertEqual(missing, set())

    def test_fake_image_model(self):
        missing = _check_protocol(FakeImageModel(), ImageModelPort)
        self.assertEqual(missing, set())

    def test_fake_tts(self):
        missing = _check_protocol(FakeTTS(), TextToSpeechPort)
        self.assertEqual(missing, set())

    def test_fake_alignment(self):
        missing = _check_protocol(FakeAlignment(), AlignmentPort)
        self.assertEqual(missing, set())

    def test_fake_media(self):
        missing = _check_protocol(FakeMedia(), MediaPort)
        self.assertEqual(missing, set())


class RealAdapterConformance(unittest.TestCase):
    """Verify real adapters satisfy their Protocol."""

    def test_openai_compatible_text(self):
        try:
            from csboard.adapters.openai_compatible.text_adapter import OpenAICompatibleTextAdapter
            adapter = OpenAICompatibleTextAdapter(api_key="test-key")
            missing = _check_protocol(adapter, TextModelPort)
            self.assertEqual(missing, set())
        except ImportError:
            self.skipTest("httpx not installed")

    def test_whiteboard_renderer(self):
        from csboard.adapters.whiteboard.renderer_adapter import WhiteboardRendererAdapter
        adapter = WhiteboardRendererAdapter()
        missing = _check_protocol(adapter, RendererPort)
        self.assertEqual(missing, set())


class WhiteboardRendererAdapterProtocol(unittest.TestCase):
    """Verify WhiteboardRendererAdapter satisfies RendererPort."""

    def test_render_method_exists(self):
        from csboard.adapters.whiteboard.renderer_adapter import WhiteboardRendererAdapter
        adapter = WhiteboardRendererAdapter()
        self.assertTrue(hasattr(adapter, "render"))
        self.assertTrue(callable(adapter.render))

    def test_capabilities_method_exists(self):
        from csboard.adapters.whiteboard.renderer_adapter import WhiteboardRendererAdapter
        adapter = WhiteboardRendererAdapter()
        self.assertTrue(hasattr(adapter, "capabilities"))
        self.assertTrue(callable(adapter.capabilities))

    def test_capabilities_returns_renderer_capabilities(self):
        from csboard.adapters.whiteboard.renderer_adapter import WhiteboardRendererAdapter
        from csboard.domain.provider_types import RendererCapabilities
        adapter = WhiteboardRendererAdapter()
        caps = adapter.capabilities()
        self.assertIsInstance(caps, RendererCapabilities)
        self.assertIn("whiteboard", caps.engines)


if __name__ == "__main__":
    unittest.main()
