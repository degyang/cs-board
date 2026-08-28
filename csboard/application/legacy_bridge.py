from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from csboard.adapters.filesystem import FilesystemProjectRepository
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.context import CommandContext, new_id, utc_now
from csboard.domain.enums import Engine, Entrypoint, ProjectStatus, RunStatus, StageStatus
from csboard.domain.errors import NotFoundError
from csboard.domain.models import Project, Run, StageState


_RUN_STATUS = {
    "queued": RunStatus.PENDING,
    "running": RunStatus.RUNNING,
    "done": RunStatus.SUCCEEDED,
    "error": RunStatus.FAILED,
    "cancelled": RunStatus.CANCELLED,
}


@dataclass(frozen=True, slots=True)
class LegacyRunLink:
    project_id: str
    run_id: str
    trace_id: str
    pipeline_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "pipeline_id": self.pipeline_id,
        }


class LegacyJobBridge:
    """Read-compatible projection of a legacy ``job.json`` into Mountain records.

    It never moves or rewrites legacy media.  The only legacy-file addition is the
    private ``_mountain`` correlation block, which is deliberately hidden from the
    existing API view.
    """

    def __init__(self, root: Path) -> None:
        self.repository = FilesystemProjectRepository(root)
        self.telemetry = JsonlTelemetry(self.repository)

    def sync(self, job_id: str, job: dict[str, Any], action: str = "legacy.sync") -> LegacyRunLink:
        link = self._link(job_id, job)
        self._ensure_records(link, job)
        signature = self._signature(job)
        mountain = job.setdefault("_mountain", {})
        if mountain.get("last_signature") != signature:
            run = self.repository.get_run(link.project_id, link.run_id)
            run.status = _RUN_STATUS.get(str(job.get("status")), RunStatus.PENDING)
            stage_name = str(job.get("current_phase") or job.get("queue_stage") or "legacy")
            run.stages[stage_name] = StageState(self._stage_status(run.status), int(job.get("resume_count", 0)))
            if run.status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}:
                run.finished_at = utc_now()
            self.repository.save_run(run)
            event = {
                "event_type": "LegacyJobStateChanged",
                "action": action,
                "legacy_job_id": job_id,
                "legacy_status": str(job.get("status", "queued")),
                "legacy_stage": str(job.get("stage", "")),
                "progress": int(job.get("progress", 0)),
            }
            self.telemetry.append_event(link.project_id, link.run_id, event)
            self.telemetry.append_log(link.project_id, link.run_id, {"level": "info", **event})
            self.telemetry.append_audit(link.project_id, link.run_id, {"action": action, "legacy_job_id": job_id})
            mountain["last_signature"] = signature
            mountain["last_synced_at"] = utc_now()
        return link

    def _link(self, job_id: str, job: dict[str, Any]) -> LegacyRunLink:
        mountain = job.setdefault("_mountain", {})
        pipeline_id = "infographic-remotion-v8" if self._is_infographic(job) else "standard-v1-legacy"
        project_id = str(mountain.setdefault("project_id", f"legacy-{job_id}"))
        run_id = str(mountain.setdefault("run_id", f"legacy-run-{job_id}"))
        trace_id = str(mountain.setdefault("trace_id", new_id("trace")))
        mountain["pipeline_id"] = pipeline_id
        mountain["schema_version"] = 1
        return LegacyRunLink(project_id, run_id, trace_id, pipeline_id)

    def _ensure_records(self, link: LegacyRunLink, job: dict[str, Any]) -> None:
        try:
            self.repository.get_project(link.project_id)
        except NotFoundError:
            engine = Engine.INFOGRAPHIC_REMOTION if link.pipeline_id.startswith("infographic") else Engine.WHITEBOARD
            self.repository.create_project(Project(
                project_id=link.project_id,
                title=str(job.get("task_name") or f"历史任务 {job.get('id', '')}")[:80],
                pipeline_id=link.pipeline_id,
                engine=engine,
                status=ProjectStatus.READY,
                created_at=utc_now(),
                updated_at=utc_now(),
            ))
        try:
            self.repository.get_run(link.project_id, link.run_id)
        except NotFoundError:
            context = CommandContext(entrypoint=Entrypoint.WEB)
            self.repository.create_run(Run(
                run_id=link.run_id,
                project_id=link.project_id,
                trace_id=link.trace_id,
                entrypoint=context.entrypoint,
                command_ids=[context.command_id],
                status=_RUN_STATUS.get(str(job.get("status")), RunStatus.PENDING),
                target_stage="legacy",
                started_at=utc_now(),
            ))

    @staticmethod
    def _is_infographic(job: dict[str, Any]) -> bool:
        return job.get("reference_mode") == "infographic" or job.get("job_type") == "infographic"

    @staticmethod
    def _signature(job: dict[str, Any]) -> str:
        return "|".join(str(job.get(key, "")) for key in ("status", "stage", "progress", "checkpoint", "queue_stage"))

    @staticmethod
    def _stage_status(status: RunStatus) -> StageStatus:
        if status is RunStatus.RUNNING:
            return StageStatus.RUNNING
        if status is RunStatus.SUCCEEDED:
            return StageStatus.SUCCEEDED
        if status is RunStatus.FAILED:
            return StageStatus.FAILED
        if status is RunStatus.CANCELLED:
            return StageStatus.CANCELLED
        return StageStatus.PENDING
