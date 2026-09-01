"""Test OpenAI-compatible text adapter with mocked HTTP."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from csboard.adapters.openai_compatible.text_adapter import OpenAITextAdapter
from csboard.domain.provider_types import TextGenerationRequest


def _mock_client(mock_client_cls: MagicMock, response: MagicMock) -> None:
    """Configure httpx.Client mock as context manager."""
    client_instance = MagicMock()
    client_instance.post.return_value = response
    mock_client_cls.return_value.__enter__ = MagicMock(return_value=client_instance)
    mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)


class OpenAITextAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = OpenAITextAdapter(
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            model="gpt-4o",
        )

    @patch("csboard.adapters.openai_compatible.text_adapter.httpx.Client")
    def test_chat_completions_happy_path(self, mock_client_cls: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.is_error = False
        mock_resp.json.return_value = {
            "model": "gpt-4o",
            "choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        _mock_client(mock_client_cls, mock_resp)

        result = self.adapter.generate(TextGenerationRequest(
            messages=[{"role": "user", "content": "hi"}],
        ))
        self.assertEqual(result.text, "hello")
        self.assertEqual(result.finish_reason, "stop")
        self.assertEqual(result.input_tokens, 10)
        self.assertEqual(result.output_tokens, 5)

    @patch("csboard.adapters.openai_compatible.text_adapter.httpx.Client")
    def test_error_raises(self, mock_client_cls: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.is_error = True
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        _mock_client(mock_client_cls, mock_resp)

        with self.assertRaises(RuntimeError) as ctx:
            self.adapter.generate(TextGenerationRequest(messages=[]))
        self.assertIn("401", str(ctx.exception))

    def test_capabilities(self) -> None:
        caps = self.adapter.capabilities()
        self.assertTrue(caps.json_schema)
        self.assertIn("gpt-4o", caps.supported_models)

    @patch("csboard.adapters.openai_compatible.text_adapter.httpx.Client")
    def test_responses_protocol(self, mock_client_cls: MagicMock) -> None:
        adapter = OpenAITextAdapter(
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            protocol="responses",
        )
        mock_resp = MagicMock()
        mock_resp.is_error = False
        mock_resp.json.return_value = {
            "model": "gpt-4o",
            "output": [{"content": [{"type": "output_text", "text": "world"}]}],
            "usage": {"input_tokens": 8, "output_tokens": 3},
        }
        _mock_client(mock_client_cls, mock_resp)

        result = adapter.generate(TextGenerationRequest(
            messages=[{"role": "user", "content": "hi"}],
        ))
        self.assertEqual(result.text, "world")


if __name__ == "__main__":
    unittest.main()
