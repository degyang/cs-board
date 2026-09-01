"""Unit tests for WhisperAlignmentAdapter.

Tests the http mode (faster-whisper-server) and the node mode (align.mjs).
All external calls are mocked.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from csboard.adapters.whisper.alignment_adapter import WhisperAlignmentAdapter
from csboard.domain.provider_types import AlignmentRequest, AlignmentResult


# ── Node mode tests ──────────────────────────────────────────────────

_NODE_OUTPUT = {
    "speechSegments": [
        {"text": "Hello world", "startMs": 0},
        {"text": "Testing one", "startMs": 2500},
    ]
}


class TestWhisperNodeMode(unittest.TestCase):
    """Test WhisperAlignmentAdapter in node mode."""

    def _run_node_adapter(
        self,
        output_data: dict | None = None,
        text: str = "Hello worldTesting one",
        returncode: int = 0,
        stderr: str = "",
    ) -> AlignmentResult:
        if output_data is None:
            output_data = _NODE_OUTPUT

        mock_result = MagicMock()
        mock_result.returncode = returncode
        mock_result.stdout = ""
        mock_result.stderr = stderr

        adapter = WhisperAlignmentAdapter(
            mode="node",
            renderer_root=Path("/tmp/renderer"),
        )

        # Mock NamedTemporaryFile to return a real path string
        mock_tmp = MagicMock()
        mock_tmp.name = "/tmp/test_align_output.json"
        mock_tmp.__enter__ = MagicMock(return_value=mock_tmp)
        mock_tmp.__exit__ = MagicMock(return_value=False)

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "is_file", return_value=True):
                with patch("tempfile.NamedTemporaryFile", return_value=mock_tmp):
                    with patch.object(
                        Path, "read_text", return_value=json.dumps(output_data)
                    ):
                        with patch.object(Path, "unlink"):
                            return adapter.align(
                                AlignmentRequest(
                                    audio_path=Path("/tmp/test.wav"), text=text
                                )
                            )

    def test_returns_alignment_result(self) -> None:
        result = self._run_node_adapter()
        self.assertIsInstance(result, AlignmentResult)

    def test_has_starts_ms(self) -> None:
        result = self._run_node_adapter()
        self.assertIsInstance(result.starts_ms, dict)

    def test_starts_ms_populated(self) -> None:
        result = self._run_node_adapter()
        self.assertGreater(len(result.starts_ms), 0)

    def test_engine_is_whisper_node(self) -> None:
        result = self._run_node_adapter()
        self.assertEqual(result.engine, "whisper-node")

    def test_node_process_failure_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            self._run_node_adapter(returncode=1, stderr="node: command not found")

    def test_missing_renderer_root_raises(self) -> None:
        adapter = WhisperAlignmentAdapter(mode="node", renderer_root=None)
        with self.assertRaises(ValueError):
            adapter.align(AlignmentRequest(audio_path=Path("/tmp/test.wav"), text="Hello"))

    def test_no_segments_returns_zero_coverage(self) -> None:
        result = self._run_node_adapter(output_data={"speechSegments": []})
        self.assertEqual(result.coverage, 0.0)
        self.assertEqual(result.reason_code, "NO_SEGMENTS")


# ── HTTP mode tests ──────────────────────────────────────────────────

_HTTP_RESPONSE = {
    "segments": [
        {
            "start": 0.0,
            "end": 2.5,
            "text": "Hello world",
            "avg_logprob": -0.3,
        },
        {
            "start": 2.5,
            "end": 5.0,
            "text": "Testing one",
            "avg_logprob": -0.4,
        },
    ]
}


class TestWhisperHTTPMode(unittest.TestCase):
    """Test WhisperAlignmentAdapter in http mode."""

    _mock_httpx: MagicMock

    def setUp(self) -> None:
        # Install mock httpx into sys.modules (lazy import inside _align_http)
        self._mock_httpx = MagicMock()
        self._mock_httpx.TimeoutException = type("TimeoutException", (Exception,), {})
        self._mock_httpx.TransportError = type("TransportError", (Exception,), {})
        self._orig_httpx = sys.modules.get("httpx")
        sys.modules["httpx"] = self._mock_httpx

        # Configure mock Client
        self._mock_client = MagicMock()
        self._mock_client.__enter__ = MagicMock(return_value=self._mock_client)
        self._mock_client.__exit__ = MagicMock(return_value=False)
        self._mock_httpx.Client.return_value = self._mock_client

    def tearDown(self) -> None:
        # Restore original httpx (or remove if it wasn't there)
        if self._orig_httpx is None:
            sys.modules.pop("httpx", None)
        else:
            sys.modules["httpx"] = self._orig_httpx

    def _make_response(
        self, status_code: int = 200, is_error: bool = False, data: dict | None = None
    ) -> MagicMock:
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.is_error = is_error
        mock_response.json.return_value = data if data is not None else _HTTP_RESPONSE
        mock_response.text = ""
        return mock_response

    def _run_http_adapter(
        self,
        response_data: dict | None = None,
        text: str = "Hello worldTesting one",
    ) -> AlignmentResult:
        self._mock_client.post.return_value = self._make_response(
            data=response_data if response_data is not None else _HTTP_RESPONSE
        )
        adapter = WhisperAlignmentAdapter(mode="http", base_url="http://localhost:8080")
        # Mock reading the audio file bytes
        with patch.object(Path, "read_bytes", return_value=b"RIFF...."):
            return adapter.align(
                AlignmentRequest(audio_path=Path("/tmp/test.wav"), text=text)
            )

    def test_returns_alignment_result(self) -> None:
        result = self._run_http_adapter()
        self.assertIsInstance(result, AlignmentResult)

    def test_engine_is_whisper_http(self) -> None:
        result = self._run_http_adapter()
        self.assertEqual(result.engine, "whisper-http")

    def test_starts_ms_populated(self) -> None:
        result = self._run_http_adapter()
        self.assertGreater(len(result.starts_ms), 0)

    def test_post_called_with_asr_url(self) -> None:
        self._run_http_adapter()
        self._mock_client.post.assert_called_once()
        call_args = self._mock_client.post.call_args
        self.assertIn("/asr", call_args[0][0])

    def test_no_segments_returns_zero_coverage(self) -> None:
        result = self._run_http_adapter(response_data={"segments": []})
        self.assertEqual(result.coverage, 0.0)
        self.assertEqual(result.reason_code, "NO_SEGMENTS")

    def test_http_error_raises(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.is_error = True
        mock_response.text = "Internal Server Error"
        self._mock_client.post.return_value = mock_response

        adapter = WhisperAlignmentAdapter(mode="http", base_url="http://localhost:8080")
        with patch.object(Path, "read_bytes", return_value=b"RIFF...."):
            with self.assertRaises(RuntimeError):
                adapter.align(
                    AlignmentRequest(audio_path=Path("/tmp/test.wav"), text="Hello")
                )

    def test_timeout_raises(self) -> None:
        self._mock_client.post.side_effect = self._mock_httpx.TimeoutException("timed out")

        adapter = WhisperAlignmentAdapter(mode="http", base_url="http://localhost:8080")
        with patch.object(Path, "read_bytes", return_value=b"RIFF...."):
            with self.assertRaises(RuntimeError):
                adapter.align(
                    AlignmentRequest(audio_path=Path("/tmp/test.wav"), text="Hello")
                )


# ── Port conformance ─────────────────────────────────────────────────

class TestWhisperPortConformance(unittest.TestCase):
    """Verify WhisperAlignmentAdapter satisfies AlignmentPort structurally."""

    def test_satisfies_alignment_port(self) -> None:
        from csboard.ports.providers import AlignmentPort
        adapter = WhisperAlignmentAdapter(mode="http", base_url="http://localhost:8080")
        self.assertIsInstance(adapter, AlignmentPort)


if __name__ == "__main__":
    unittest.main()
