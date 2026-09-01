"""Test IndexTTS adapter with mocked HTTP."""

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from csboard.adapters.indextts.tts_adapter import IndexTTSAdapter, _probe_duration_ms
from csboard.domain.provider_types import TTSRequest


def _make_wav(duration_ms: int = 1000, sample_rate: int = 24000) -> bytes:
    num_samples = int(sample_rate * duration_ms / 1000)
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    return header + b"\x00" * data_size


def _mock_client(mock_client_cls: MagicMock, response: MagicMock) -> None:
    client_instance = MagicMock()
    client_instance.post.return_value = response
    mock_client_cls.return_value.__enter__ = MagicMock(return_value=client_instance)
    mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)


class IndexTTSAdapterTest(unittest.TestCase):
    def test_requires_reference_audio(self) -> None:
        adapter = IndexTTSAdapter()
        with self.assertRaises(ValueError):
            adapter.synthesize(TTSRequest(text="你好"))

    @patch("csboard.adapters.indextts.tts_adapter.httpx.Client")
    def test_fastapi_mode(self, mock_client_cls: MagicMock) -> None:
        wav = _make_wav(2000)
        mock_resp = MagicMock()
        mock_resp.is_error = False
        mock_resp.content = wav
        _mock_client(mock_client_cls, mock_resp)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as ref:
            ref.write(b"\x00" * 100)
            ref_path = Path(ref.name)

        try:
            adapter = IndexTTSAdapter(mode="fastapi")
            result = adapter.synthesize(TTSRequest(text="你好", reference_audio=ref_path))
            self.assertEqual(result.audio, wav)
            self.assertGreater(result.duration_ms, 0)
            self.assertEqual(result.model, "indextts")
        finally:
            ref_path.unlink()

    def test_probe_duration(self) -> None:
        wav = _make_wav(3000)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav)
            f_path = Path(f.name)
        try:
            duration = _probe_duration_ms(f_path)
            self.assertAlmostEqual(duration, 3000, delta=50)
        finally:
            f_path.unlink()


if __name__ == "__main__":
    unittest.main()
