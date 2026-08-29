from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from csboard.adapters.filesystem import FilesystemProjectRepository
from csboard.adapters.filesystem import FilesystemArtifactStore
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.context import CommandContext, new_id, utc_now
from csboard.domain.enums import Engine, Entrypoint, ProjectStatus, RunStatus, StageStatus
from csboard.domain.errors import NotFoundError
from csboard.domain.models import Project, Run, StageState
from csboard.domain.av_timing import segment_script
from csboard.application.av_artifacts import av_plan_document, json_bytes


@dataclass(slots=True)
class MountainCommands:
    """Entry-point-neutral commands used by CLI now and Web/Skills later."""

    root: Path
    repository: FilesystemProjectRepository = field(init=False)
    telemetry: JsonlTelemetry = field(init=False)

    def __post_init__(self) -> None:
        self.repository = FilesystemProjectRepository(self.root)
        self.telemetry = JsonlTelemetry(self.repository)

    def create_project(
        self,
        title: str,
        pipeline_id: str = "mountain-av-v1",
        engine: Engine = Engine.WHITEBOARD,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        if not title.strip():
            raise ValueError("项目名称不能为空")
        if pipeline_id != "mountain-av-v1" or engine is not Engine.WHITEBOARD:
            raise ValueError("M04 仅支持标准 whiteboard 的 mountain-av-v1；自定义参考和动态信息图将在 M09 开放")
        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        project_id = new_id("project")
        run_id = new_id("run")
        trace_id = new_id("trace")
        project = Project(
            project_id=project_id,
            title=title.strip()[:80],
            pipeline_id=pipeline_id,
            engine=engine,
            status=ProjectStatus.READY,
            created_at=utc_now(),
            updated_at=utc_now(),
            active_run_id=run_id,
        )
        run = Run(
            run_id=run_id,
            project_id=project_id,
            trace_id=trace_id,
            entrypoint=context.entrypoint,
            command_ids=[context.command_id],
            status=RunStatus.PENDING,
            target_stage="compose-video",
            started_at=utc_now(),
        )
        self.repository.create_project(project)
        self.repository.create_run(run)
        event = self.telemetry.append_event(project_id, run_id, {
            "event_type": "ProjectCreated",
            "command": "project.create",
            "pipeline_id": pipeline_id,
            "engine": engine.value,
        })
        self.telemetry.append_audit(project_id, run_id, {
            "action": "project.create",
            "command_id": context.command_id,
            "entrypoint": context.entrypoint.value,
        })
        return self._ok("project.create", project, run, context, event_sequence=event["sequence"])

    def show_project(self, project_id: str) -> dict[str, Any]:
        project = self.repository.get_project(project_id)
        run = self.repository.get_run(project_id, project.active_run_id) if project.active_run_id else None
        return {"ok": True, "project": project.to_dict(), "active_run": run.to_dict() if run else None}

    def trace_run(self, project_id: str, run_id: str) -> dict[str, Any]:
        run = self.repository.get_run(project_id, run_id)
        return {"ok": True, "project_id": project_id, "run_id": run_id, "trace_id": run.trace_id, "command_ids": run.command_ids, "status": run.status.value}

    def list_events(self, project_id: str, run_id: str, after_sequence: int = 0) -> dict[str, Any]:
        events = self.telemetry.read_events(project_id, run_id, after_sequence)
        return {"ok": True, "project_id": project_id, "run_id": run_id, "items": events, "next_cursor": events[-1]["sequence"] if events else after_sequence}

    def list_logs(self, project_id: str, run_id: str) -> dict[str, Any]:
        path = self.repository.run_dir(project_id, run_id) / "observability" / "logs.jsonl"
        self.repository.get_run(project_id, run_id)
        items = [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        return {"ok": True, "project_id": project_id, "run_id": run_id, "items": items}

    def export_diagnostics(self, project_id: str, run_id: str) -> dict[str, Any]:
        path = self.telemetry.export_diagnostic_bundle(project_id, run_id)
        return {"ok": True, "project_id": project_id, "run_id": run_id, "bundle": str(path)}

    def segment_script(self, project_id: str, run_id: str, script: str, context: CommandContext | None = None) -> dict[str, Any]:
        run = self.repository.get_run(project_id, run_id)
        project = self.repository.get_project(project_id)
        if project.pipeline_id != "mountain-av-v1":
            raise ValueError("仅 mountain-av-v1 可运行标准文案分割")
        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        run.status = RunStatus.RUNNING
        units = segment_script(script)
        document = av_plan_document(project_id, run_id, units, script, project.engine)
        artifact = FilesystemArtifactStore(self.repository).commit_bytes(
            project_id, run_id, "planning.av-plan", "planning/av-plan.json", json_bytes(document), "segment-script"
        )
        run.command_ids.append(context.command_id)
        run.stages["segment-script"] = StageState(StageStatus.SUCCEEDED, 1)
        self.repository.save_run(run)
        event = self.telemetry.append_event(project_id, run_id, {"event_type": "ScriptSegmented", "unit_count": len(units), "visual_count": sum(len(unit.visual_items) for unit in units)})
        self.telemetry.append_audit(project_id, run_id, {"action": "stage.run", "stage": "segment-script", "command_id": context.command_id})
        return {"ok": True, "command": "stage.run", "project_id": project_id, "run_id": run_id, "trace_id": run.trace_id, "command_id": context.command_id, "stage": "segment-script", "result": "succeeded", "artifacts": [artifact.artifact_key], "event_sequence": event["sequence"], "warnings": [], "next_stage": "clone-voice"}

    @staticmethod
    def _ok(command: str, project: Project, run: Run, context: CommandContext, **extra: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "command": command,
            "project_id": project.project_id,
            "run_id": run.run_id,
            "trace_id": run.trace_id,
            "command_id": context.command_id,
            **extra,
        }
