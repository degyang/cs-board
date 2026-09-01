from __future__ import annotations

import unittest
from pathlib import Path

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


class TextGenerationTest(unittest.TestCase):
    def test_request_defaults(self) -> None:
        req = TextGenerationRequest(messages=[{"role": "user", "content": "hi"}])
        self.assertEqual(req.model, "")
        self.assertEqual(req.max_tokens, 4096)
        self.assertEqual(req.temperature, 0.7)
        self.assertIsNone(req.json_schema)

    def test_result_defaults(self) -> None:
        res = TextGenerationResult(text="hello")
        self.assertEqual(res.finish_reason, "stop")
        self.assertEqual(res.input_tokens, 0)
        self.assertEqual(res.output_tokens, 0)
        self.assertEqual(res.provider_metadata, {})

    def test_request_frozen(self) -> None:
        req = TextGenerationRequest(messages=[])
        with self.assertRaises(AttributeError):
            req.model = "other"  # type: ignore[misc]

    def test_result_frozen(self) -> None:
        res = TextGenerationResult(text="x")
        with self.assertRaises(AttributeError):
            res.text = "y"  # type: ignore[misc]


class ImageGenerationTest(unittest.TestCase):
    def test_request_defaults(self) -> None:
        req = ImageGenerationRequest(prompt="a cat")
        self.assertEqual(req.width, 1024)
        self.assertEqual(req.height, 1024)
        self.assertEqual(req.n, 1)
        self.assertEqual(req.response_format, "b64_json")
        self.assertIsNone(req.reference_image)

    def test_result_frozen(self) -> None:
        res = ImageGenerationResult(images=(b"\x89PNG",))
        with self.assertRaises(AttributeError):
            res.images = ()  # type: ignore[misc]


class TTSTest(unittest.TestCase):
    def test_request_defaults(self) -> None:
        req = TTSRequest(text="你好")
        self.assertEqual(req.language, "zh")
        self.assertEqual(req.sample_rate, 24000)
        self.assertIsNone(req.reference_audio)

    def test_result_frozen(self) -> None:
        res = TTSResult(audio=b"\x00", duration_ms=1000)
        self.assertEqual(res.channels, 1)


class AlignmentTest(unittest.TestCase):
    def test_request_requires_path(self) -> None:
        req = AlignmentRequest(audio_path=Path("/tmp/test.wav"), text="hello")
        self.assertEqual(req.language, "zh")

    def test_result_with_reason(self) -> None:
        res = AlignmentResult(starts_ms={}, reason_code="LOW_COVERAGE")
        self.assertEqual(res.reason_code, "LOW_COVERAGE")


class RenderTest(unittest.TestCase):
    def test_request_defaults(self) -> None:
        req = RenderRequest(
            timeline_path=Path("/tmp/timeline.json"),
            storyboard_path=Path("/tmp/storyboard.json"),
            illustration_manifest_path=Path("/tmp/illust.json"),
            output_dir=Path("/tmp/out"),
        )
        self.assertEqual(req.engine, "whiteboard")

    def test_capabilities_defaults(self) -> None:
        caps = RendererCapabilities()
        self.assertIn("whiteboard", caps.engines)


class MediaProbeTest(unittest.TestCase):
    def test_defaults(self) -> None:
        probe = MediaProbeResult()
        self.assertEqual(probe.duration_ms, 0)
        self.assertEqual(probe.width, 0)


if __name__ == "__main__":
    unittest.main()
