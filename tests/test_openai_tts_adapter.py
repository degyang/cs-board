import base64
from unittest.mock import Mock, patch

from csboard.adapters.openai_compatible.tts_adapter import OpenAITTSAdapter
from csboard.domain.provider_types import TTSRequest


def test_openai_tts_payload_and_response_are_normalized():
    response = Mock(status_code=200, headers={"x-request-id": "req-1"})
    response.json.return_value = {"audio": base64.b64encode(b"wav").decode()}
    with patch("httpx.post", return_value=response) as post:
        result = OpenAITTSAdapter("https://provider.test/v1", "secret", "mimo-v2.5-tts,other").synthesize(
            TTSRequest(text="hello", voice_id="bingtang", voice_config={"instruction": "warm"})
        )
    post.assert_called_once()
    payload = post.call_args.kwargs["json"]
    assert payload["model"] == "mimo-v2.5-tts"
    assert payload["audio"] == {"format": "wav", "voice": "bingtang"}
    assert payload["messages"] == [{"role": "user", "content": "warm"}, {"role": "assistant", "content": "hello"}]
    assert result.audio == b"wav"


def test_openai_tts_error_does_not_expose_secret():
    response = Mock(status_code=500, headers={})
    response.raise_for_status.side_effect = RuntimeError("secret")
    with patch("httpx.post", return_value=response):
        try:
            OpenAITTSAdapter("https://provider.test/v1", "top-secret", "mimo").synthesize(TTSRequest(text="x"))
        except RuntimeError as exc:
            assert str(exc) == "TTS_PROVIDER_REQUEST_FAILED"
            assert "top-secret" not in str(exc)
            assert "Authorization" not in str(exc)
