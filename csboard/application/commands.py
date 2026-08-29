from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from csboard.adapters.filesystem import FilesystemProjectRepository
from csboard.adapters.filesystem import FilesystemArtifactStore
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.av_artifacts import av_plan_document, json_bytes
from csboard.application.composition import CompositionService
from csboard.application.context import CommandContext, new_id, utc_now
from csboard.application.illustrations import IllustrationService
from csboard.application.pipeline import PipelineOrchestrator
from csboard.application.storyboard import StoryboardService
from csboard.application.voice_units import VoiceUnitService
from csboard.domain.av_timing import VoiceUnit, segment_script
from csboard.domain.enums import Engine, Entrypoint, ProjectStatus, RunStatus, StageStatus
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.models import Project, Run, StageState
from csboard.ports.providers import AlignmentPort, ImageModelPort, MediaPort, RendererPort, TextModelPort, TextToSpeechPort


@dataclass(slots=True)
class MountainCommands:
    """Entry-point-neutral commands used by CLI now and Web/Skills later."""

    root: Path
    repository: FilesystemProjectRepository = field(init=False)
    telemetry: JsonlTelemetry = field(init=False)
    pipeline: PipelineOrchestrator = field(init=False)

    def __post_init__(self) -> None:
        self.repository = FilesystemProjectRepository(self.root)
        self.telemetry = JsonlTelemetry(self.repository)
        self.pipeline = PipelineOrchestrator(
            get_run=self.repository.get_run,
            save_run=self.repository.save_run,
            append_event=self.telemetry.append_event,
        )
        # Register implemented stage executors
        self.pipeline.register_stage("segment-script", self._exec_segment_script)
        self.pipeline.register_stage("clone-voice", self._exec_clone_voice)
        self.pipeline.register_stage("plan-storyboard", self._exec_plan_storyboard)
        self.pipeline.register_stage("generate-illustrations", self._exec_generate_illustrations)
        self.pipeline.register_stage("render-visuals", self._exec_render_visuals)
        self.pipeline.register_stage("compose-video", self._exec_compose_video)

    def create_project(
        self,
        title: str,
        pipeline_id: str = "mountain-av-v1",
        engine: Engine = Engine.WHITEBOARD,
        request: dict[str, Any] | None = None,
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
        # Store project request for pipeline orchestration
        if request:
            request_path = self.repository.project_dir(project_id) / "request.json"
            request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
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

    def clone_voice(
        self,
        project_id: str,
        run_id: str,
        tts: TextToSpeechPort,
        alignment: AlignmentPort,
        media: MediaPort,
        reference_audio: Path,
        unit_id: str | None = None,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        run = self.repository.get_run(project_id, run_id)
        project = self.repository.get_project(project_id)
        if project.pipeline_id != "mountain-av-v1":
            raise ValueError("仅 mountain-av-v1 可运行 clone-voice")

        # Read av-plan artifact to get voice units
        av_plan_ref = FilesystemArtifactStore(self.repository).get(project_id, run_id, "planning.av-plan")
        if not av_plan_ref:
            raise ValueError("请先运行 segment-script 生成 av-plan")
        import json
        av_plan_path = self.repository.run_dir(project_id, run_id) / "artifacts" / av_plan_ref["relative_path"]
        av_plan = json.loads(av_plan_path.read_text(encoding="utf-8"))

        # Reconstruct VoiceUnit objects
        units: list[VoiceUnit] = []
        for u in av_plan.get("voice_units", []):
            from csboard.domain.av_timing import TextRange, VisualItem
            visuals = tuple(
                VisualItem(
                    visual_id=v["visual_id"],
                    order=v["order"],
                    source_range=TextRange(v["source_range"]["start"], v["source_range"]["end"]),
                    text=v["text"],
                )
                for v in u.get("visual_items", [])
            )
            units.append(VoiceUnit(
                unit_id=u["unit_id"],
                order=u["order"],
                source_range=TextRange(u["source_range"]["start"], u["source_range"]["end"]),
                text=u["text"],
                visual_items=visuals,
            ))

        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        run.status = RunStatus.RUNNING
        run.command_ids.append(context.command_id)
        self.repository.save_run(run)

        service = VoiceUnitService(tts, alignment, media, self.repository, reference_audio)
        manifest, timeline = service.run(
            project_id, run_id, tuple(units),
            profile="default", engine=project.engine,
        )

        event = self.telemetry.append_event(project_id, run_id, {
            "event_type": "CloneVoiceSucceeded",
            "unit_count": len(units),
        })
        self.telemetry.append_audit(project_id, run_id, {
            "action": "stage.run",
            "stage": "clone-voice",
            "command_id": context.command_id,
        })

        return {
            "ok": True,
            "command": "stage.run",
            "project_id": project_id,
            "run_id": run_id,
            "trace_id": run.trace_id,
            "command_id": context.command_id,
            "stage": "clone-voice",
            "result": "succeeded",
            "artifacts": ["audio.voice-manifest", "timing.timeline"],
            "event_sequence": event["sequence"],
            "warnings": run.warnings,
            "next_stage": "plan-storyboard",
        }

    def artifact_show(
        self,
        project_id: str,
        run_id: str,
        artifact_key: str,
    ) -> dict[str, Any]:
        """Return the content of an artifact by key."""
        self.repository.get_run(project_id, run_id)  # validate run exists
        store = FilesystemArtifactStore(self.repository)
        ref = store.get(project_id, run_id, artifact_key)
        if not ref:
            raise NotFoundError(f"Artifact {artifact_key} 不存在")
        run_dir = self.repository.run_dir(project_id, run_id)
        artifact_path = run_dir / "artifacts" / ref["relative_path"]
        if not artifact_path.exists():
            raise NotFoundError(f"Artifact 文件不存在: {ref['relative_path']}")
        # Parse JSON artifacts, return raw for others
        if artifact_path.suffix == ".json":
            content = json.loads(artifact_path.read_text(encoding="utf-8"))
        else:
            content = artifact_path.read_text(encoding="utf-8")
        return {
            "ok": True,
            "command": "artifact.show",
            "project_id": project_id,
            "run_id": run_id,
            "artifact_key": artifact_key,
            "content": content,
            "metadata": ref,
        }

    def stage_retry(
        self,
        project_id: str,
        run_id: str,
        stage: str,
        unit_id: str | None = None,
        visual_id: str | None = None,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Retry a stage, optionally scoped to a specific unit or visual."""
        run = self.repository.get_run(project_id, run_id)
        context = context or CommandContext(entrypoint=Entrypoint.CLI)

        # Reset the stage status
        stage_state = run.stages.get(stage)
        if stage_state is None:
            raise NotFoundError(f"阶段 {stage} 未在运行中注册")
        if stage_state.status not in (StageStatus.FAILED, StageStatus.SUCCEEDED, StageStatus.STALE):
            raise DomainError("INVALID_STATE", f"阶段 {stage} 当前状态为 {stage_state.status.value}，无法重试")

        # Mark downstream stages as stale
        from csboard.application.pipeline import STAGE_ORDER
        try:
            stage_idx = STAGE_ORDER.index(stage)
        except ValueError:
            raise DomainError("VALIDATION_ERROR", f"未知阶段: {stage}")
        for downstream in STAGE_ORDER[stage_idx + 1:]:
            if downstream in run.stages:
                run.stages[downstream].status = StageStatus.STALE

        # Reset target stage
        run.stages[stage] = StageState(StageStatus.PENDING, stage_state.attempt)
        run.status = RunStatus.RUNNING
        run.command_ids.append(context.command_id)
        self.repository.save_run(run)

        self.telemetry.append_event(project_id, run_id, {
            "event_type": "StageRetryRequested",
            "stage": stage,
            "unit_id": unit_id,
            "visual_id": visual_id,
        })
        self.telemetry.append_audit(project_id, run_id, {
            "action": "stage.retry",
            "stage": stage,
            "command_id": context.command_id,
            "unit_id": unit_id,
            "visual_id": visual_id,
        })

        # Execute the stage via pipeline
        result = self.pipeline.run_pipeline(
            project_id, run_id,
            policy="targeted",
            target_stage=stage,
            context=context,
        )
        return result

    def pipeline_run(
        self,
        project_id: str,
        run_id: str | None = None,
        policy: str = "auto",
        target_stage: str | None = None,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Run the pipeline with the given policy."""
        project = self.repository.get_project(project_id)
        if run_id is None:
            run_id = project.active_run_id
        if not run_id:
            raise NotFoundError("项目没有活跃的运行")
        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        self.telemetry.append_audit(project_id, run_id, {
            "action": "pipeline.run",
            "policy": policy,
            "command_id": context.command_id,
        })
        return self.pipeline.run_pipeline(project_id, run_id, policy, target_stage, context)

    def pipeline_resume(
        self,
        project_id: str,
        run_id: str | None = None,
        policy: str = "auto",
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Resume a pipeline from the last successful stage."""
        project = self.repository.get_project(project_id)
        if run_id is None:
            run_id = project.active_run_id
        if not run_id:
            raise NotFoundError("项目没有活跃的运行")
        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        self.telemetry.append_audit(project_id, run_id, {
            "action": "pipeline.resume",
            "policy": policy,
            "command_id": context.command_id,
        })
        return self.pipeline.resume_pipeline(project_id, run_id, policy, context)

    # ── Stage executor wrappers ──────────────────────────────────────

    def _exec_segment_script(self, project_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for segment-script. Reads script from project request."""
        request = self._read_request(project_id)
        script = request.get("script", "")
        if not script:
            raise DomainError("VALIDATION_ERROR", "项目请求中缺少 script 字段")
        return self.segment_script(project_id, run_id, script, context)

    def _exec_clone_voice(self, project_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for clone-voice. Reads config from project request."""
        request = self._read_request(project_id)
        reference_audio = request.get("reference_audio")
        if not reference_audio:
            raise DomainError("VALIDATION_ERROR", "项目请求中缺少 reference_audio 字段")
        tts_url = request.get("tts_url", "http://127.0.0.1:7860")
        tts_mode = request.get("tts_mode", "gradio")
        from csboard.adapters.indextts.tts_adapter import IndexTTSAdapter
        from csboard.adapters.whisper.alignment_adapter import WhisperAlignmentAdapter
        from csboard.adapters.ffmpeg.media_adapter import FFmpegMediaAdapter
        tts = IndexTTSAdapter(base_url=tts_url, mode=tts_mode)
        alignment = WhisperAlignmentAdapter(
            mode=request.get("whisper_mode", "node"),
            renderer_root=Path(request.get("whisper_renderer_root", Path(__file__).resolve().parents[2] / "video_renderer")),
            base_url=request.get("whisper_url", "http://127.0.0.1:9000"),
        )
        media = FFmpegMediaAdapter()
        return self.clone_voice(
            project_id, run_id, tts, alignment, media,
            reference_audio=Path(reference_audio),
            context=context,
        )

    def _read_request(self, project_id: str) -> dict[str, Any]:
        """Read the project request.json if it exists."""
        request_path = self.repository.project_dir(project_id) / "request.json"
        if request_path.exists():
            return json.loads(request_path.read_text(encoding="utf-8"))
        return {}

    def plan_storyboard(
        self,
        project_id: str,
        run_id: str,
        text_model: TextModelPort,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Generate storyboard for all Visual Items."""
        run = self.repository.get_run(project_id, run_id)
        project = self.repository.get_project(project_id)
        context = context or CommandContext(entrypoint=Entrypoint.CLI)

        run.status = RunStatus.RUNNING
        run.stages["plan-storyboard"] = StageState(StageStatus.RUNNING, 1)
        run.command_ids.append(context.command_id)
        self.repository.save_run(run)

        service = StoryboardService(text_model, self.repository)
        result = service.run(project_id, run_id, project.engine)

        run.stages["plan-storyboard"] = StageState(StageStatus.SUCCEEDED, 1)
        self.repository.save_run(run)

        event = self.telemetry.append_event(project_id, run_id, {
            "event_type": "StoryboardGenerated",
            "visual_count": result["visual_count"],
        })
        self.telemetry.append_audit(project_id, run_id, {
            "action": "stage.run",
            "stage": "plan-storyboard",
            "command_id": context.command_id,
        })

        return {
            "ok": True,
            "command": "stage.run",
            "project_id": project_id,
            "run_id": run_id,
            "trace_id": run.trace_id,
            "command_id": context.command_id,
            "stage": "plan-storyboard",
            "result": "succeeded",
            "artifacts": [result["artifact_key"]],
            "event_sequence": event["sequence"],
            "warnings": [],
            "next_stage": "generate-illustrations",
        }

    def generate_illustrations(
        self,
        project_id: str,
        run_id: str,
        image_model: ImageModelPort,
        visual_id: str | None = None,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Generate illustrations for Visual Items."""
        run = self.repository.get_run(project_id, run_id)
        project = self.repository.get_project(project_id)
        context = context or CommandContext(entrypoint=Entrypoint.CLI)

        run.status = RunStatus.RUNNING
        run.stages["generate-illustrations"] = StageState(StageStatus.RUNNING, 1)
        run.command_ids.append(context.command_id)
        self.repository.save_run(run)

        service = IllustrationService(image_model, self.repository)
        result = service.run(project_id, run_id, project.engine, visual_id)

        run.stages["generate-illustrations"] = StageState(StageStatus.SUCCEEDED, 1)
        self.repository.save_run(run)

        event = self.telemetry.append_event(project_id, run_id, {
            "event_type": "IllustrationsGenerated",
            "image_count": result["image_count"],
        })
        self.telemetry.append_audit(project_id, run_id, {
            "action": "stage.run",
            "stage": "generate-illustrations",
            "command_id": context.command_id,
        })

        return {
            "ok": True,
            "command": "stage.run",
            "project_id": project_id,
            "run_id": run_id,
            "trace_id": run.trace_id,
            "command_id": context.command_id,
            "stage": "generate-illustrations",
            "result": "succeeded",
            "artifacts": [result["artifact_key"]],
            "event_sequence": event["sequence"],
            "warnings": [],
            "next_stage": "render-visuals",
        }

    def _exec_plan_storyboard(self, project_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for plan-storyboard."""
        text_model = self._text_model_from_request(project_id)
        return self.plan_storyboard(project_id, run_id, text_model, context)

    def _exec_generate_illustrations(self, project_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for generate-illustrations."""
        image_model = self._image_model_from_request(project_id)
        return self.generate_illustrations(project_id, run_id, image_model, context=context)

    def render_visuals(
        self,
        project_id: str,
        run_id: str,
        renderer: RendererPort,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Render video clips for all Visual Items."""
        from csboard.application.av_artifacts import read_manifest
        from csboard.domain.provider_types import RenderRequest

        run = self.repository.get_run(project_id, run_id)
        project = self.repository.get_project(project_id)
        context = context or CommandContext(entrypoint=Entrypoint.CLI)

        run.status = RunStatus.RUNNING
        run.stages["render-visuals"] = StageState(StageStatus.RUNNING, 1)
        run.command_ids.append(context.command_id)
        self.repository.save_run(run)

        run_dir = self.repository.run_dir(project_id, run_id)
        store = FilesystemArtifactStore(self.repository)
        def artifact_path(key: str) -> Path | None:
            ref = store.get(project_id, run_id, key)
            return run_dir / "artifacts" / ref["relative_path"] if ref else None
        timeline_path = artifact_path("timing.timeline")
        storyboard_path = artifact_path("planning.storyboard")
        illustration_manifest_path = artifact_path("illustrations.manifest")

        if timeline_path is None or not timeline_path.exists():
            raise DomainError("VALIDATION_ERROR", "timeline 不存在，请先运行 clone-voice")
        if storyboard_path is None or not storyboard_path.exists():
            raise DomainError("VALIDATION_ERROR", "storyboard 不存在，请先运行 plan-storyboard")
        if illustration_manifest_path is None or not illustration_manifest_path.exists():
            raise DomainError("VALIDATION_ERROR", "illustration-manifest 不存在，请先运行 generate-illustrations")

        # Create output directory
        output_dir = run_dir / "render"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build render request
        request = RenderRequest(
            timeline_path=timeline_path,
            storyboard_path=storyboard_path,
            illustration_manifest_path=illustration_manifest_path,
            output_dir=output_dir,
            request_id=f"{project_id}:{run_id}:render",
        )

        # Execute render
        result = renderer.render(request)

        # Build render manifest
        render_manifest = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "engine": project.engine.value,
            "total_duration_ms": result.duration_ms,
            "total_frames": result.frames,
            "clips": result.provider_metadata.get("clips", []),
            "output_path": str(result.output_path.relative_to(self.repository.root)),
        }

        artifact_key = store.commit_bytes(
            project_id, run_id, "render.manifest", "render/render-manifest.json",
            json_bytes(render_manifest), "render-visuals",
        ).artifact_key

        run.stages["render-visuals"] = StageState(StageStatus.SUCCEEDED, 1)
        self.repository.save_run(run)

        event = self.telemetry.append_event(project_id, run_id, {
            "event_type": "RenderCompleted",
            "clip_count": len(render_manifest.get("clips", [])),
            "total_duration_ms": result.duration_ms,
        })
        self.telemetry.append_audit(project_id, run_id, {
            "action": "stage.run",
            "stage": "render-visuals",
            "command_id": context.command_id,
        })

        return {
            "ok": True,
            "command": "stage.run",
            "project_id": project_id,
            "run_id": run_id,
            "trace_id": run.trace_id,
            "command_id": context.command_id,
            "stage": "render-visuals",
            "result": "succeeded",
            "artifacts": [artifact_key],
            "event_sequence": event["sequence"],
            "warnings": [],
            "next_stage": "compose-video",
        }

    def compose_video(
        self,
        project_id: str,
        run_id: str,
        media: MediaPort,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Compose final video from rendered clips and audio."""
        run = self.repository.get_run(project_id, run_id)
        project = self.repository.get_project(project_id)
        context = context or CommandContext(entrypoint=Entrypoint.CLI)

        run.status = RunStatus.RUNNING
        run.stages["compose-video"] = StageState(StageStatus.RUNNING, 1)
        run.command_ids.append(context.command_id)
        self.repository.save_run(run)

        service = CompositionService(media, self.repository)
        result = service.run(project_id, run_id)

        run.stages["compose-video"] = StageState(StageStatus.SUCCEEDED, 1)
        run.status = RunStatus.COMPLETED
        self.repository.save_run(run)

        event = self.telemetry.append_event(project_id, run_id, {
            "event_type": "CompositionCompleted",
            "output_path": result["output_path"],
            "duration_ms": result["duration_ms"],
        })
        self.telemetry.append_audit(project_id, run_id, {
            "action": "stage.run",
            "stage": "compose-video",
            "command_id": context.command_id,
        })

        return {
            "ok": True,
            "command": "stage.run",
            "project_id": project_id,
            "run_id": run_id,
            "trace_id": run.trace_id,
            "command_id": context.command_id,
            "stage": "compose-video",
            "result": "succeeded",
            "artifacts": [result["artifact_key"]],
            "event_sequence": event["sequence"],
            "warnings": [],
            "next_stage": None,
        }

    def _exec_render_visuals(self, project_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for render-visuals."""
        from csboard.adapters.whiteboard.renderer_adapter import WhiteboardRendererAdapter
        renderer = WhiteboardRendererAdapter()
        return self.render_visuals(project_id, run_id, renderer, context)

    def _exec_compose_video(self, project_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for compose-video."""
        from csboard.adapters.ffmpeg.media_adapter import FFmpegMediaAdapter
        media = FFmpegMediaAdapter()
        return self.compose_video(project_id, run_id, media, context)

    def _provider_config(self, project_id: str, kind: str) -> dict[str, Any]:
        config = self._read_request(project_id).get("providers", {}).get(kind, {})
        if not isinstance(config, dict) or not config.get("base_url"):
            raise DomainError("CAPABILITY_NOT_AVAILABLE", f"未配置 {kind} provider")
        api_key = config.get("api_key")
        if not api_key and config.get("api_key_env"):
            api_key = os.environ.get(str(config["api_key_env"]))
        if not api_key:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", f"{kind} provider 缺少 API Key")
        return {**config, "api_key": api_key}

    def _text_model_from_request(self, project_id: str) -> TextModelPort:
        from csboard.adapters.openai_compatible.text_adapter import OpenAITextAdapter
        config = self._provider_config(project_id, "text")
        return OpenAITextAdapter(config["base_url"], config["api_key"], config.get("model", "gpt-4o"), config.get("protocol", "chat_completions"))

    def _image_model_from_request(self, project_id: str) -> ImageModelPort:
        from csboard.adapters.openai_compatible.image_adapter import OpenAIImageAdapter
        config = self._provider_config(project_id, "image")
        return OpenAIImageAdapter(config["base_url"], config["api_key"], config.get("model", "dall-e-3"))

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
