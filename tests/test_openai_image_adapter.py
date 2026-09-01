"""Test OpenAI-compatible image adapter with mocked HTTP."""

from __future__ import annotations

import base64
import unittest
from unittest.mock import MagicMock, patch

from csboard.adapters.openai_compatible.image_adapter import OpenAIImageAdapter
from csboard.domain.provider_types import ImageGenerationRequest


def _mock_client(mock_client_cls: MagicMock, response: MagicMock) -> None:
    """Configure httpx.Client mock as context manager."""
    client_instance = MagicMock()
    client_instance.post.return_value = response
    mock_client_cls.return_value.__enter__ = MagicMock(return_value=client_instance)
    mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)


class OpenAIImageAdapterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = OpenAIImageAdapter(
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            model="dall-e-3",
        )

    @patch("csboard.adapters.openai_compatible.image_adapter.httpx.Client")
    def test_standard_generation_b64(self, mock_client_cls: MagicMock) -> None:
        img_b64 = base64.b64encode(b"\x89PNG fake").decode()
        mock_resp = MagicMock()
        mock_resp.is_error = False
        mock_resp.json.return_value = {
            "model": "dall-e-3",
            "data": [{"b64_json": img_b64, "revised_prompt": "a cute cat"}],
        }
        _mock_client(mock_client_cls, mock_resp)

        result = self.adapter.generate(ImageGenerationRequest(prompt="a cat"))
        self.assertEqual(len(result.images), 1)
        self.assertEqual(result.images[0], b"\x89PNG fake")
        self.assertEqual(result.revised_prompt, "a cute cat")

    @patch("csboard.adapters.openai_compatible.image_adapter.httpx.Client")
    def test_error_raises(self, mock_client_cls: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.is_error = True
        mock_resp.status_code = 429
        mock_resp.text = "Rate limited"
        _mock_client(mock_client_cls, mock_resp)

        with self.assertRaises(RuntimeError):
            self.adapter.generate(ImageGenerationRequest(prompt="a cat"))

    def test_capabilities(self) -> None:
        caps = self.adapter.capabilities()
        self.assertTrue(caps.reference_image)
        self.assertTrue(caps.image_edit)
        self.assertIn("dall-e-3", caps.supported_models)


if __name__ == "__main__":
    unittest.main()
