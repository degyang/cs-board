"""Whisper-based audio alignment adapter.

Supports two modes:
- ``node`` (default): calls the existing ``video_renderer/align.mjs`` script
  via Node.js, matching the legacy pipeline.
- ``http``: calls a Whisper HTTP service (e.g. faster-whisper-server).
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from difflib import SequenceMatcher
from pathlib import Path

from csboard.domain.provider_types import AlignmentRequest, AlignmentResult


class WhisperAlignmentAdapter:
    """AlignmentPort implementation backed by Whisper.

    Parameters
    ----------
    mode:
        ``"node"`` uses the local ``align.mjs`` script.
        ``"http"`` posts to a Whisper HTTP API.
    renderer_root:
        Path to ``video_renderer/`` directory (required for node mode).
    whisper_model:
        Whisper model size (e.g. ``"medium"``).
    base_url:
        HTTP endpoint (required for http mode).
    timeout:
        Subprocess/HTTP timeout in seconds.
    """

    def __init__(
        self,
        mode: str = "node",
        renderer_root: Path | None = None,
        whisper_model: str = "medium",
        base_url: str = "http://127.0.0.1:9000",
        timeout: float = 300.0,
    ) -> None:
        self._mode = mode
        self._renderer_root = renderer_root
        self._model = whisper_model
        self._base = base_url.rstrip("/")
        self._timeout = timeout

    def align(self, request: AlignmentRequest) -> AlignmentResult:
        if self._mode == "node":
            return self._align_node(request)
        return self._align_http(request)

    # ── Node.js mode ─────────────────────────────────────────────────

    def _align_node(self, request: AlignmentRequest) -> AlignmentResult:
        if self._renderer_root is None:
            raise ValueError("renderer_root is required for node mode")

        align_script = self._renderer_root / "align.mjs"
        if not align_script.is_file():
            raise FileNotFoundError(f"align.mjs not found: {align_script}")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_path = Path(tmp.name)

        try:
            env = {"INFOGRAPHIC_WHISPER_MODEL": self._model}
            result = subprocess.run(
                ["node", str(align_script), str(request.audio_path), str(output_path)],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                env={**__import__("os").environ, **env},
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Whisper alignment failed: {result.stderr[:500] or result.stdout[:500]}"
                )

            return self._parse_alignment_output(output_path, request.text)
        finally:
            output_path.unlink(missing_ok=True)

    def _parse_alignment_output(self, path: Path, text: str) -> AlignmentResult:
        """Parse the JSON output from align.mjs into AlignmentResult."""
        data = json.loads(path.read_text(encoding="utf-8"))
        # align.mjs schema v2 puts recognised text and timestamps in
        # `captions`; speechSegments contains silence boundaries only.
        segments = data.get("captions") or data.get("speechSegments", [])
        if not segments:
            return AlignmentResult(
                starts_ms={},
                coverage=0.0,
                confidence=0.0,
                engine="whisper-node",
                reason_code="NO_SEGMENTS",
            )

        # Build character-offset timestamps.  A character value is ambiguous
        # for repeated characters, whereas offsets can be mapped deterministically
        # to each VisualItem source range by the domain timing service.
        recognised_chars: list[str] = []
        recognised_times: list[int] = []
        confidences: list[float] = []
        for seg in segments:
            seg_text = str(seg.get("text", "")).strip()
            start_ms = int(seg["startMs"]) if "startMs" in seg else int(float(seg.get("start", 0)) * 1000)
            end_ms = int(seg["endMs"]) if "endMs" in seg else int(float(seg.get("end", start_ms / 1000)) * 1000)
            clean = [char.lower() for char in seg_text if re.match(r"[\w\u3400-\u9fff]", char)]
            for offset, char in enumerate(clean):
                recognised_chars.append(char)
                recognised_times.append(start_ms + ((end_ms - start_ms) * offset // max(len(clean), 1)))
            if "confidence" in seg:
                confidences.append(float(seg["confidence"]))

        source = [(char.lower(), index) for index, char in enumerate(text)
                  if re.match(r"[\w\u3400-\u9fff]", char)]
        matcher = SequenceMatcher(None, [item[0] for item in source], recognised_chars, autojunk=False)
        starts_ms: dict[str, int] = {}
        matched = 0
        for block in matcher.get_matching_blocks():
            matched += block.size
            for offset in range(block.size):
                raw_index = source[block.a + offset][1]
                starts_ms[f"char:{raw_index}"] = recognised_times[block.b + offset]
        coverage = matched / max(len(source), 1)
        confidence = sum(confidences) / len(confidences) if confidences else 0.9

        return AlignmentResult(
            starts_ms=starts_ms,
            coverage=coverage,
            confidence=confidence,
            engine="whisper-node",
        )

    # ── HTTP mode ────────────────────────────────────────────────────

    def _align_http(self, request: AlignmentRequest) -> AlignmentResult:
        import httpx

        url = f"{self._base}/asr"
        params = {"output": "json", "language": request.language or "zh"}
        files = {"audio_file": (request.audio_path.name, request.audio_path.read_bytes(), "audio/wav")}

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(url, params=params, files=files)
            if resp.is_error:
                raise RuntimeError(f"Whisper HTTP error: {resp.status_code} {resp.text[:500]}")
            data = resp.json()
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise RuntimeError(f"Whisper HTTP request failed: {exc}") from exc

        return self._parse_http_response(data, request.text)

    def _parse_http_response(self, data: dict, text: str) -> AlignmentResult:
        """Parse faster-whisper-server JSON response."""
        segments = data.get("segments", [])
        if not segments:
            return AlignmentResult(
                starts_ms={},
                coverage=0.0,
                confidence=0.0,
                engine="whisper-http",
                reason_code="NO_SEGMENTS",
            )

        starts_ms: dict[str, int] = {}
        char_index = 0
        for seg in segments:
            seg_text = str(seg.get("text", "")).strip()
            start_sec = float(seg.get("start", 0))
            start_ms = int(start_sec * 1000)
            end_ms = int(float(seg.get("end", start_sec)) * 1000)
            for offset, _ in enumerate(seg_text):
                if char_index < len(text):
                    starts_ms[f"char:{char_index}"] = start_ms + ((end_ms - start_ms) * offset // max(len(seg_text), 1))
                    char_index += 1

        total_chars = len(text.strip())
        matched = min(char_index, total_chars)
        coverage = matched / max(total_chars, 1)
        avg_prob = 0.0
        if segments:
            probs = [float(s.get("avg_logprob", -0.5)) for s in segments]
            avg_prob = max(0.0, min(1.0, sum(probs) / len(probs) + 1.0))

        return AlignmentResult(
            starts_ms=starts_ms,
            coverage=coverage,
            confidence=avg_prob,
            engine="whisper-http",
        )
