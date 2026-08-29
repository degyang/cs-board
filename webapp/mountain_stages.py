from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import httpx

from csboard.adapters.filesystem import FilesystemProjectRepository
from csboard.adapters.filesystem import FilesystemArtifactStore
from csboard.application.voice_units import SynthesizedVoice, VoiceUnitService
from csboard.domain.av_timing import AlignmentResult, TextRange, VisualItem, VoiceUnit
from csboard.domain.enums import RunStatus, StageStatus
from csboard.domain.models import StageState


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


def submit_legacy_full_pipeline(root: Path, project_id: str, run_id: str) -> str:
    """Bridge mature execution into a Mountain Run; the browser never sees legacy state."""
    repo = FilesystemProjectRepository(root)
    request = repo.read_json(repo.project_dir(project_id) / "inputs" / "request.json")
    reference = repo.project_dir(project_id) / "inputs" / request["reference_path"]
    with reference.open("rb") as audio, httpx.Client(timeout=30) as client:
        response = client.post("http://127.0.0.1:8000/api/jobs", data={
            "copy": request["script"], "task_name": repo.get_project(project_id).title,
            "style": request.get("style", "极简粗线简笔白板风"),
            "include_subtitles": str(bool(request.get("include_subtitles", True))).lower(),
            "pen_text": request.get("pen_text", ""), "stroke_detail": request.get("stroke_detail", "detailed"),
        }, files={"reference": (reference.name, audio, "audio/wav")})
    response.raise_for_status()
    legacy_id = str(response.json()["id"])
    thread = threading.Thread(target=_sync_legacy, args=(root, project_id, run_id, legacy_id), daemon=True)
    thread.start()
    return legacy_id


def _sync_legacy(root: Path, project_id: str, run_id: str, legacy_id: str) -> None:
    repo = FilesystemProjectRepository(root)
    while True:
        try:
            job = httpx.get(f"http://127.0.0.1:8000/api/jobs/{legacy_id}", timeout=15).json()
            run = repo.get_run(project_id, run_id)
            _project_legacy_stages(run, job)
            if job.get("status") == "done":
                result_name = str(job.get("result_file") or "final.mp4")
                final = root / "jobs" / legacy_id / result_name
                if final.exists():
                    FilesystemArtifactStore(repo).commit_bytes(
                        project_id, run_id, "output.final-video", "output/final.mp4", final.read_bytes(), "compose-video"
                    )
                run.status = RunStatus.SUCCEEDED
                repo.save_run(run); return
            if job.get("status") in {"error", "cancelled"}:
                run.status = RunStatus.FAILED if job.get("status") == "error" else RunStatus.CANCELLED
                run.warnings.append({"code": "LEGACY_PIPELINE", "message": str(job.get("error") or job.get("stage"))})
                repo.save_run(run); return
            repo.save_run(run)
        except Exception:
            return
        time.sleep(2)


def _project_legacy_stages(run, job: dict) -> None:
    """Project legacy progress into the canonical six Stage names without guessing success."""
    status = str(job.get("status") or "")
    progress = int(job.get("progress") or 0)
    phase = str(job.get("current_phase") or job.get("queue_stage") or "")
    checkpoint = str(job.get("checkpoint") or "")
    completed = {"segment-script"}
    if progress >= 14 or phase in {"model", "render"}:
        completed.add("clone-voice")
    if checkpoint in {"plan_done", "images", "render"} or phase == "render":
        completed.add("storyboard")
    if checkpoint in {"images", "render"} or phase == "render":
        completed.add("illustrate")
    if checkpoint == "render" or status == "done":
        completed.add("whiteboard")
    if status == "done":
        completed.add("compose")
    ordered = ["segment-script", "clone-voice", "storyboard", "illustrate", "whiteboard", "compose"]
    active = {"voice": "clone-voice", "model": "storyboard", "render": "whiteboard"}.get(phase)
    if status in {"error", "cancelled"}:
        active = active or next((name for name in ordered if name not in completed), "compose")
    for name in ordered:
        if name in completed:
            stage_status = StageStatus.SUCCEEDED
        elif name == active:
            stage_status = StageStatus.FAILED if status == "error" else StageStatus.CANCELLED if status == "cancelled" else StageStatus.RUNNING
        else:
            stage_status = StageStatus.PENDING
        previous = run.stages.get(name)
        attempt = previous.attempt if previous else 0
        run.stages[name] = StageState(stage_status, max(1, attempt) if stage_status is not StageStatus.PENDING else attempt)
