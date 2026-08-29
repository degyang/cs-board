from __future__ import annotations

import json
from pathlib import Path

from csboard.adapters.filesystem import FilesystemProjectRepository
from csboard.application.voice_units import SynthesizedVoice, VoiceUnitService
from csboard.domain.av_timing import AlignmentResult, TextRange, VisualItem, VoiceUnit


class LegacyTtsAdapter:
    def __init__(self, reference: Path) -> None: self.reference = reference
    def synthesize(self, unit: VoiceUnit) -> SynthesizedVoice:
        from webapp import server
        temporary = self.reference.parent / f"{unit.unit_id}.partial.wav"
        server.synthesize_voice(server.load_config(), self.reference, unit.text, temporary)
        duration = int(round(server.probe_duration(temporary) * 1000))
        payload = temporary.read_bytes(); temporary.unlink(missing_ok=True)
        return SynthesizedVoice(payload, duration)


class FallbackAligner:
    def align(self, unit: VoiceUnit, voice: SynthesizedVoice) -> AlignmentResult:
        return AlignmentResult({}, 0, 0, reason_code="ALIGNMENT_ADAPTER_NOT_CONFIGURED")


def clone_voice(root: Path, project_id: str, run_id: str) -> tuple[dict, dict]:
    repo = FilesystemProjectRepository(root)
    request = repo.read_json(repo.project_dir(project_id) / "inputs" / "request.json")
    plan = repo.read_json(repo.run_dir(project_id, run_id) / "artifacts" / "planning" / "av-plan.json")
    units = tuple(VoiceUnit(
        item["unit_id"], int(item["order"]), TextRange(**item["source_range"]), item["text"],
        tuple(VisualItem(v["visual_id"], int(v["order"]), TextRange(**v["source_range"]), v["text"]) for v in item["visual_items"]),
    ) for item in plan["voice_units"])
    reference = repo.project_dir(project_id) / "inputs" / request["reference_path"]
    return VoiceUnitService(repo, LegacyTtsAdapter(reference), FallbackAligner()).run(project_id, run_id, units, "legacy-tts")
