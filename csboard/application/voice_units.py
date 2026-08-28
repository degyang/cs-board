from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

from csboard.adapters.filesystem import FilesystemArtifactStore, FilesystemProjectRepository
from csboard.application.av_artifacts import json_bytes, timeline_document
from csboard.domain.av_timing import AlignmentResult, UnitTiming, VoiceUnit, time_voice_unit
from csboard.domain.enums import Engine


@dataclass(frozen=True, slots=True)
class SynthesizedVoice:
    audio: bytes
    duration_ms: int
    sample_rate: int = 24000
    channels: int = 1


class VoiceSynthesizer(Protocol):
    def synthesize(self, unit: VoiceUnit) -> SynthesizedVoice: ...


class VoiceAligner(Protocol):
    def align(self, unit: VoiceUnit, voice: SynthesizedVoice) -> AlignmentResult | None: ...


class VoiceUnitService:
    """Unit-level durable synthesis; an invalid alignment never discards valid audio."""

    def __init__(self, repository: FilesystemProjectRepository, synthesizer: VoiceSynthesizer, aligner: VoiceAligner) -> None:
        self.repository, self.synthesizer, self.aligner = repository, synthesizer, aligner
        self.artifacts = FilesystemArtifactStore(repository)

    def run(self, project_id: str, run_id: str, units: tuple[VoiceUnit, ...], profile: str, engine: Engine = Engine.WHITEBOARD) -> tuple[dict, dict]:
        voices, timings = [], []
        for unit in units:
            key = f"audio.{unit.unit_id}"
            existing = self.artifacts.get(project_id, run_id, key)
            if existing and existing.get("status") == "succeeded":
                payload = (self.repository.run_dir(project_id, run_id) / "artifacts" / existing["relative_path"]).read_bytes()
                voice = SynthesizedVoice(payload, int(existing["duration_ms"]), int(existing.get("sample_rate", 24000)), int(existing.get("channels", 1)))
            else:
                voice = self.synthesizer.synthesize(unit)
                reference = self.artifacts.commit_bytes(project_id, run_id, key, f"media/voices/{unit.unit_id}.wav", voice.audio, "clone-voice")
                stored = self.artifacts.get(project_id, run_id, key)
                stored.update({"duration_ms": voice.duration_ms, "sample_rate": voice.sample_rate, "channels": voice.channels})
                index = self.repository.run_dir(project_id, run_id) / "artifacts" / "index.json"
                self.repository.write_json(index, {"schema_version": 1, "artifacts": {**self.repository.read_json(index)["artifacts"], key: stored}})
            alignment = self.aligner.align(unit, voice)
            timing = time_voice_unit(unit, voice.duration_ms, alignment)
            timings.append(timing)
            item = self.artifacts.get(project_id, run_id, key)
            voices.append({"unit_id": unit.unit_id, "audio_path": f"artifacts/{item['relative_path']}", "sha256": f"sha256:{hashlib.sha256(voice.audio).hexdigest()}", "duration_ms": voice.duration_ms, "sample_rate": voice.sample_rate, "channels": voice.channels, "tts_profile": profile, "attempt": 1})
        manifest = {"schema_version": 1, "artifact_type": "voice-manifest", "artifact_key": "audio.voice-manifest", "voices": voices}
        timeline = timeline_document(project_id, run_id, tuple(timings), engine)
        self.artifacts.commit_bytes(project_id, run_id, "audio.voice-manifest", "audio/voice-manifest.json", json_bytes(manifest), "clone-voice")
        self.artifacts.commit_bytes(project_id, run_id, "timing.timeline", "timing/timeline.json", json_bytes(timeline), "clone-voice")
        return manifest, timeline
