"""Test all fake adapters — happy path, failure injection, latency."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from csboard.adapters.fakes import (
    FakeAlignment,
    FakeImageModel,
    FakeMedia,
    FakeRenderer,
    FakeTextModel,
    FakeTTS,
)
from csboard.domain.provider_types import (
    AlignmentRequest,
    ImageGenerationRequest,
    MediaProbeResult,
    RenderRequest,
    TextGenerationRequest,
    TTSRequest,
)


class FakeTextModelTest(unittest.TestCase):
    def test_happy_path(self) -> None:
        fake = FakeTextModel(response_text="hello world")
        result = fake.generate(TextGenerationRequest(messages=[{"role": "user", "content": "hi"}]))
        self.assertEqual(result.text, "hello world")
        self.assertEqual(result.finish_reason, "stop")
        self.assertEqual(fake.call_count, 1)

    def test_failure_injection(self) -> None:
        fake = FakeTextModel(should_fail=True)
        with self.assertRaises(RuntimeError):
            fake.generate(TextGenerationRequest(messages=[]))

    def test_capabilities(self) -> None:
        caps = FakeTextModel().capabilities()
        self.assertTrue(caps.json_schema)
        self.assertIn("fake-text", caps.supported_models)


class FakeImageModelTest(unittest.TestCase):
    def test_happy_path(self) -> None:
        fake = FakeImageModel()
        result = fake.generate(ImageGenerationRequest(prompt="cat", n=2))
        self.assertEqual(len(result.images), 2)
        self.assertEqual(fake.call_count, 1)

    def test_failure_injection(self) -> None:
        fake = FakeImageModel(should_fail=True)
        with self.assertRaises(RuntimeError):
            fake.generate(ImageGenerationRequest(prompt="cat"))


class FakeTTSTest(unittest.TestCase):
    def test_happy_path(self) -> None:
        fake = FakeTTS(duration_ms=2000)
        result = fake.synthesize(TTSRequest(text="你好"))
        self.assertEqual(result.duration_ms, 2000)
        self.assertGreater(len(result.audio), 0)

    def test_failure_injection(self) -> None:
        fake = FakeTTS(should_fail=True)
        with self.assertRaises(RuntimeError):
            fake.synthesize(TTSRequest(text="你好"))


class FakeAlignmentTest(unittest.TestCase):
    def test_happy_path(self) -> None:
        fake = FakeAlignment()
        result = fake.align(AlignmentRequest(audio_path=Path("/tmp/x.wav"), text="abc"))
        self.assertEqual(result.coverage, 1.0)
        self.assertEqual(result.confidence, 0.95)

    def test_failure_returns_failed_result(self) -> None:
        fake = FakeAlignment(should_fail=True)
        result = fake.align(AlignmentRequest(audio_path=Path("/tmp/x.wav"), text="abc"))
        self.assertEqual(result.coverage, 0.0)
        self.assertEqual(result.reason_code, "ALIGNMENT_FAILED")


class FakeRendererTest(unittest.TestCase):
    def test_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeRenderer()
            out = Path(tmp) / "out"
            result = fake.render(RenderRequest(
                timeline_path=Path("/tmp/t.json"),
                storyboard_path=Path("/tmp/s.json"),
                illustration_manifest_path=Path("/tmp/i.json"),
                output_dir=out,
            ))
            self.assertEqual(result.frames, 150)
            self.assertTrue(result.output_path.exists())

    def test_failure_injection(self) -> None:
        fake = FakeRenderer(should_fail=True)
        with self.assertRaises(RuntimeError):
            fake.render(RenderRequest(
                timeline_path=Path("/tmp/t.json"),
                storyboard_path=Path("/tmp/s.json"),
                illustration_manifest_path=Path("/tmp/i.json"),
                output_dir=Path("/tmp/out"),
            ))


class FakeMediaTest(unittest.TestCase):
    def test_probe(self) -> None:
        fake = FakeMedia(duration_ms=8000)
        result = fake.probe(Path("/tmp/test.mp4"))
        self.assertEqual(result.duration_ms, 8000)
        self.assertEqual(result.codec, "h264")

    def test_normalize_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeMedia()
            inp = Path(tmp) / "in.wav"
            out = Path(tmp) / "out.wav"
            inp.write_bytes(b"\x00")
            fake.normalize(inp, out)
            self.assertTrue(out.exists())

    def test_concat_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeMedia()
            out = Path(tmp) / "concat.mp4"
            fake.concat([Path("/tmp/a.mp4"), Path("/tmp/b.mp4")], out)
            self.assertTrue(out.exists())

    def test_subtitle_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeMedia()
            out = Path(tmp) / "subtitled.mp4"
            fake.subtitle(Path("/tmp/v.mp4"), Path("/tmp/s.srt"), out)
            self.assertTrue(out.exists())

    def test_failure_injection(self) -> None:
        fake = FakeMedia(should_fail=True)
        with self.assertRaises(RuntimeError):
            fake.probe(Path("/tmp/test.mp4"))


if __name__ == "__main__":
    unittest.main()
