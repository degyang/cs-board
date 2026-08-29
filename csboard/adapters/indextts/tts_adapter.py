"""IndexTTS adapter — supports both Gradio and FastAPI endpoints."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

import httpx

from csboard.domain.provider_types import TTSRequest, TTSResult


class IndexTTSAdapter:
    """Wraps an IndexTTS service (Gradio or FastAPI).

    Parameters
    ----------
    base_url:
        Root URL of the IndexTTS service, e.g. ``http://127.0.0.1:7860``.
    mode:
        ``"gradio"`` (default) uses the Gradio Python client.
        ``"fastapi"`` posts directly to ``/api/tts``.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:7860",
        mode: str = "gradio",
        timeout: float = 1800.0,
        max_retries: int = 4,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._mode = mode
        self._timeout = timeout
        self._max_retries = max_retries

    def synthesize(self, request: TTSRequest) -> TTSResult:
        if request.reference_audio is None:
            raise ValueError("IndexTTS requires a reference audio file")

        if self._mode == "fastapi":
            return self._synthesize_fastapi(request)
        return self._synthesize_gradio(request)

    # ── FastAPI mode ─────────────────────────────────────────────────

    def _synthesize_fastapi(self, request: TTSRequest) -> TTSResult:
        url = f"{self._base}/api/tts"
        audio_path = request.reference_audio
        assert audio_path is not None

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            with httpx.Client(timeout=self._timeout) as client, audio_path.open("rb") as audio:
                resp = client.post(
                    url,
                    data={"text": request.text, "emo_weight": "0.65"},
                    files={"voice": (audio_path.name, audio, "audio/wav")},
                )
            if resp.is_error:
                raise RuntimeError(f"IndexTTS FastAPI error: {resp.status_code} {resp.text[:500]}")

            tmp_path.write_bytes(resp.content)
            duration_ms = _probe_duration_ms(tmp_path)
            return TTSResult(
                audio=resp.content,
                duration_ms=duration_ms,
                sample_rate=request.sample_rate,
                channels=1,
                model="indextts",
                request_id=request.request_id,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    # ── Gradio mode ──────────────────────────────────────────────────

    def _synthesize_gradio(self, request: TTSRequest) -> TTSResult:
        try:
            from gradio_client import Client, handle_file  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "gradio_client is required for IndexTTS Gradio mode. "
                "Install it with: pip install gradio_client"
            )

        audio_path = request.reference_audio
        assert audio_path is not None

        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                client = Client(self._base, verbose=False, httpx_kwargs={"timeout": self._timeout})
                job = client.submit(
                    "Same as the voice reference",
                    handle_file(str(audio_path)),
                    request.text,
                    None,  # optional emotion-reference audio
                    0.65,
                    0, 0, 0, 0, 0, 0, 0, 0, "", False, 120,
                    1.0, True, 0.8, 30, 0.8, 0.0, 3, 10.0, 1500,
                    api_name="/gen_single",
                )
                result = job.result(timeout=self._timeout)
                wav_path = _extract_gradio_path(result)
                audio_bytes = wav_path.read_bytes()
                duration_ms = _probe_duration_ms(wav_path)
                return TTSResult(
                    audio=audio_bytes,
                    duration_ms=duration_ms,
                    sample_rate=request.sample_rate,
                    channels=1,
                    model="indextts",
                    request_id=request.request_id,
                )
            except Exception as exc:
                last_exc = exc
                message = str(exc).lower()
                retryable = any(
                    token in message
                    for token in ("10061", "connection refused", "connecterror", "timed out")
                )
                if not retryable or attempt == self._max_retries - 1:
                    break
                import time
                time.sleep(5 * (attempt + 1))

        raise RuntimeError(f"IndexTTS synthesis failed: {last_exc}")


# ── helpers ──────────────────────────────────────────────────────────

def _extract_gradio_path(result: Any) -> Path:
    """Unwrap Gradio's nested return formats into a file Path."""
    item: Any = result
    while True:
        if isinstance(item, (list, tuple)) and item:
            item = item[0]
            continue
        if isinstance(item, dict) and "value" in item and not item.get("path"):
            item = item["value"]
            continue
        break

    if isinstance(item, dict):
        path_value = item.get("path")
        if path_value and Path(path_value).exists():
            return Path(path_value)
        if item.get("url"):
            with httpx.Client(timeout=300) as http:
                resp = http.get(item["url"])
                resp.raise_for_status()
            tmp = Path(tempfile.mktemp(suffix=".wav"))
            tmp.write_bytes(resp.content)
            return tmp
        raise RuntimeError(f"IndexTTS returned unrecognised file object: {list(item.keys())}")
    if isinstance(item, (str, Path)):
        p = Path(item)
        if p.exists():
            return p
    raise RuntimeError(f"IndexTTS returned unsupported format: {type(item).__name__}")


def _probe_duration_ms(path: Path) -> int:
    """Estimate WAV duration from file size (PCM 16-bit mono)."""
    try:
        import struct
        with path.open("rb") as f:
            f.seek(22)  # channels offset in WAV header
            channels = struct.unpack("<H", f.read(2))[0]
            f.seek(28)  # byte_rate offset
            byte_rate = struct.unpack("<I", f.read(4))[0]
        if byte_rate > 0 and channels > 0:
            size = path.stat().st_size - 44  # subtract WAV header
            return int(size / byte_rate * 1000)
    except Exception:
        pass
    return 0
