"""Voice Units — local TTS via IndexTTS, XTTS or OpenAI-compatible endpoint.

Handles the ``clone-voice`` stage of the pipeline.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from csboard.adapters.filesystem import FilesystemArtifactStore, FilesystemProjectRepository
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.av_artifacts import json_bytes, timeline_document, voice_manifest_document, read_manifest, save_json_artifact
from csboard.domain.av_timing import AlignmentResult, UnitTiming, VoiceUnit, time_voice_unit
from csboard.domain.enums import Engine, StageStatus
from csboard.domain.models import StageState


class VoiceSynthesizer(Protocol):
    """Minimal interface any TTS backend must satisfy."""

    def synthesize(self, text: str, voice_ref: Path, output_path: Path, **kwargs: Any) -> Path:
        """Synthesize *text* with the reference voice and write audio to *output_path*."""
        ...


class VoiceAligner(Protocol):
    def align(self, unit: VoiceUnit, voice: Any) -> AlignmentResult | None: ...


@dataclass(frozen=True, slots=True)
class SynthesizedVoice:
    audio: bytes
    duration_ms: int
    sample_rate: int = 24000
    channels: int = 1


@dataclass
class VoiceUnit:
    unit_id: str
    text: str
    voice_ref: Path
    duration_ms: int | None = None
    audio_path: str | None = None
    error: str | None = None


@dataclass
class VoiceUnitResult:
    """Result from processing a single voice unit."""
    unit_id: str
    audio_path: str | None = None
    duration_ms: int | None = None
    error: str | None = None


@dataclass
class VoiceManifest:
    units: list[VoiceUnitResult]
    total_duration_ms: int
    provider: str


class VoiceUnitService:
    """Unit-level durable synthesis; an invalid alignment never discards valid audio."""

    def __init__(
        self,
        tts: Any,
        alignment: Any,
        media: Any,
        repository: FilesystemProjectRepository,
        reference_audio: Path,
    ) -> None:
        self.tts = tts
        self.alignment = alignment
        self.media = media
        self.repository = repository
        self.reference_audio = reference_audio
        self.artifacts = FilesystemArtifactStore(repository)
        self.telemetry = JsonlTelemetry(repository)

    def run(
        self,
        project_id: str,
        run_id: str,
        units: tuple[VoiceUnit, ...],
        profile: str,
        engine: Engine = Engine.WHITEBOARD,
    ) -> tuple[dict, dict]:
        voices, timings = [], []
        for unit in units:
            self.telemetry.append_event(project_id, run_id, {"event_type": "VoiceUnitStarted", "unit_id": unit.unit_id})
            key = f"audio.{unit.unit_id}"
            existing = self.artifacts.get(project_id, run_id, key)

            if existing and existing.get("status") == "succeeded":
                payload = (self.repository.run_dir(project_id, run_id) / "artifacts" / existing["relative_path"]).read_bytes()
                voice = SynthesizedVoice(payload, int(existing["duration_ms"]), int(existing.get("sample_rate", 24000)), int(existing.get("channels", 1)))
            else:
                # Synthesize voice using TTSRequest
                from csboard.domain.provider_types import TTSRequest
                request = TTSRequest(
                    text=unit.text,
                    voice_id="default",
                    reference_audio=self.reference_audio,
                )
                result = self.tts.synthesize(request)
                voice = SynthesizedVoice(
                    result.audio,
                    result.duration_ms,
                    result.sample_rate,
                    result.channels,
                )
                # Save to artifacts
                self.repository.run_dir(project_id, run_id).mkdir(parents=True, exist_ok=True)
                voice_dir = self.repository.run_dir(project_id, run_id) / "artifacts" / "media" / "voices"
                voice_dir.mkdir(parents=True, exist_ok=True)
                (voice_dir / f"{unit.unit_id}.wav").write_bytes(voice.audio)

                reference = self.artifacts.commit_bytes(
                    project_id, run_id, key,
                    f"media/voices/{unit.unit_id}.wav",
                    voice.audio, "clone-voice",
                )
                stored = self.artifacts.get(project_id, run_id, key)
                stored.update({"duration_ms": voice.duration_ms, "sample_rate": voice.sample_rate, "channels": voice.channels})
                index = self.repository.run_dir(project_id, run_id) / "artifacts" / "index.json"
                self.repository.write_json(index, {"schema_version": 1, "artifacts": {**self.repository.read_json(index)["artifacts"], key: stored}})

            # Align using AlignmentRequest
            try:
                from csboard.domain.provider_types import AlignmentRequest
                align_request = AlignmentRequest(
                    audio_path=self.repository.run_dir(project_id, run_id) / "artifacts" / f"media/voices/{unit.unit_id}.wav",
                    text=unit.text,
                )
                alignment_result = self.alignment.align(align_request)
            except Exception:
                alignment_result = AlignmentResult({}, 0, 0, reason_code="ALIGNMENT_EXECUTION_FAILED")

            timing = time_voice_unit(unit, voice.duration_ms, alignment_result)
            self.telemetry.append_event(project_id, run_id, {
                "event_type": "AlignmentFallback" if timing.timing_source.value == "equal_fallback" else "AlignmentSucceeded",
                "unit_id": unit.unit_id, "timing_source": timing.timing_source.value,
                "reason_code": timing.alignment.get("reason_code"), "duration_ms": voice.duration_ms,
            })
            timings.append(timing)

            item = self.artifacts.get(project_id, run_id, key)
            voices.append({
                "unit_id": unit.unit_id,
                "audio_path": f"artifacts/{item['relative_path']}",
                "duration_ms": voice.duration_ms,
                "sample_rate": voice.sample_rate,
                "channels": voice.channels,
                "tts_profile": profile,
                "attempt": 1,
            })
            self.telemetry.append_event(project_id, run_id, {"event_type": "VoiceUnitSucceeded", "unit_id": unit.unit_id, "duration_ms": voice.duration_ms})

        manifest = voice_manifest_document(project_id, run_id, voices, engine)
        timeline = timeline_document(project_id, run_id, tuple(timings), engine)
        self.artifacts.commit_bytes(project_id, run_id, "audio.voice-manifest", "audio/voice-manifest.json", json_bytes(manifest), "clone-voice")
        self.artifacts.commit_bytes(project_id, run_id, "timing.timeline", "timing/timeline.json", json_bytes(timeline), "clone-voice")

        run = self.repository.get_run(project_id, run_id)
        run.stages["clone-voice"] = StageState(StageStatus.SUCCEEDED, 1)
        for item in timings:
            if item.timing_source.value == "equal_fallback":
                warning = {"code": "ALIGNMENT_EQUAL_FALLBACK", "unit_id": item.unit_id, "message": "该单元已按图片数量等分实际语音时长"}
                if warning not in run.warnings:
                    run.warnings.append(warning)
        self.repository.save_run(run)

        return manifest, timeline


def build_voice_manifest(
    project_id: str,
    run_id: str,
    synthesizer: VoiceSynthesizer,
    *,
    repository: Any | None = None,
    skip_existing: bool = True,
) -> dict[str, Any]:
    """Generate voice manifest from a timeline.

    Parameters
    ----------
    project_id, run_id:
        Identifiers for locating the run directory.
    synthesizer:
        TTS backend instance.
    repository:
        Optional repository for reading timeline manifest.
    skip_existing:
        Skip units whose audio files already exist on disk.

    Returns
    -------
    dict
        Voice manifest with per-unit results and aggregate stats.
    """
    project_dir = Path("projects") / project_id
    run_dir = project_dir / "runs" / run_id
    audio_dir = run_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Read timeline
    timeline = read_manifest(project_id, run_id, "timeline")

    units: list[VoiceUnitResult] = []
    total_duration = 0
    errors: list[str] = []

    for segment in timeline.get("units", []):
        unit_id = segment.get("unit_id", str(uuid.uuid4())[:8])
        text = segment.get("text", "")
        voice_ref = segment.get("voice_ref", "")
        expected_duration = segment.get("duration_ms")

        audio_path = audio_dir / f"{unit_id}.wav"

        # Skip if already generated
        if skip_existing and audio_path.exists():
            duration_ms = expected_duration or 0
            units.append(VoiceUnitResult(
                unit_id=unit_id,
                audio_path=f"audio/{unit_id}.wav",
                duration_ms=duration_ms,
            ))
            total_duration += duration_ms
            continue

        try:
            # Resolve voice reference
            voice_ref_path = project_dir / voice_ref if voice_ref else None
            if voice_ref_path and not voice_ref_path.exists():
                raise FileNotFoundError(f"Voice reference not found: {voice_ref}")

            # Synthesize
            result_path = synthesizer.synthesize(
                text=text,
                voice_ref=voice_ref_path,
                output_path=audio_path,
            )

            duration_ms = expected_duration
            if result_path.exists() and duration_ms is None:
                # Estimate duration from file size (rough: 16kHz, 16-bit mono)
                file_size = result_path.stat().st_size
                duration_ms = int(file_size / 32)  # 16000 * 2 bytes/sample

            units.append(VoiceUnitResult(
                unit_id=unit_id,
                audio_path=f"audio/{unit_id}.wav",
                duration_ms=duration_ms,
            ))
            total_duration += duration_ms or 0

        except Exception as exc:
            errors.append(f"{unit_id}: {str(exc)}")
            units.append(VoiceUnitResult(
                unit_id=unit_id,
                error=str(exc),
            ))

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provider": synthesizer.__class__.__name__,
        "total_duration_ms": total_duration,
        "unit_count": len(units),
        "error_count": len(errors),
        "units": [
            {
                "unit_id": u.unit_id,
                "audio_path": u.audio_path,
                "duration_ms": u.duration_ms,
                "error": u.error,
            }
            for u in units
        ],
    }


def save_voice_manifest(
    project_id: str,
    run_id: str,
    manifest: dict[str, Any],
) -> Path:
    """Persist voice manifest to artifacts."""
    return save_json_artifact(
        project_id=project_id,
        run_id=run_id,
        filename="voice-manifest.json",
        data=manifest,
    )


def read_voice_manifest(project_id: str, run_id: str) -> dict[str, Any]:
    """Read voice manifest from artifacts."""
    return read_manifest(project_id, run_id, "voice-manifest.json")
