from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from csboard.adapters.filesystem import FilesystemTaskRepository
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
from csboard.domain.script_preparation import prepare_script
from csboard.domain.enums import Engine, Entrypoint, TaskStatus, RunStatus, StageStatus
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.models import Task, Run, StageState
from csboard.ports.providers import AlignmentPort, ImageModelPort, MediaPort, RendererPort, TextModelPort, TextToSpeechPort


@dataclass(slots=True)
class MountainCommands:
    """Entry-point-neutral commands used by CLI now and Web/Skills later.

    service_resolver: 动态服务解析器（用于获取 ServiceDefinition）
    provider_factory: 适配器工厂（用于 create_adapter(service_definition)）
    """

    root: Path
    provider_factory: Any | None = None  # ProviderFactory for real adapters
    service_resolver: Any | None = None  # ServiceResolver for dynamic resolution
    repository: FilesystemTaskRepository = field(init=False)
    telemetry: JsonlTelemetry = field(init=False)
    pipeline: PipelineOrchestrator = field(init=False)

    def __post_init__(self) -> None:
        self.repository = FilesystemTaskRepository(self.root)
        self.telemetry = JsonlTelemetry(self.repository)
        self.pipeline = PipelineOrchestrator(
            get_run=self.repository.get_run,
            save_run=self.repository.save_run,
            append_event=self.telemetry.append_event,
        )
        # Register implemented stage executors
        self.pipeline.register_stage("generate-visual-anchors", self._exec_generate_visual_anchors)
        self.pipeline.register_stage("clone-voice", self._exec_clone_voice)
        self.pipeline.register_stage("plan-storyboard", self._exec_plan_storyboard)
        self.pipeline.register_stage("generate-illustrations", self._exec_generate_illustrations)
        self.pipeline.register_stage("render-visuals", self._exec_render_visuals)
        self.pipeline.register_stage("compose-video", self._exec_compose_video)

    def create_task(
        self,
        title: str,
        pipeline_id: str = "mountain-av-v1",
        engine: Engine = Engine.WHITEBOARD,
        request: dict[str, Any] | None = None,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        if not title.strip():
            raise ValueError("任务名称不能为空")
        if pipeline_id != "mountain-av-v1" or engine is not Engine.WHITEBOARD:
            raise ValueError("M04 仅支持标准 whiteboard 的 mountain-av-v1；自定义参考和动态信息图将在 M09 开放")
        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        task_id = new_id("task")
        run_id = new_id("run")
        trace_id = new_id("trace")
        task = Task(
            task_id=task_id,
            title=title.strip()[:80],
            pipeline_id=pipeline_id,
            engine=engine,
            status=TaskStatus.READY,
            created_at=utc_now(),
            updated_at=utc_now(),
            active_run_id=run_id,
        )
        run = Run(
            run_id=run_id,
            task_id=task_id,
            trace_id=trace_id,
            entrypoint=context.entrypoint,
            command_ids=[context.command_id],
            status=RunStatus.PENDING,
            target_stage="compose-video",
            started_at=utc_now(),
        )
        self.repository.create_task(task)
        self.repository.create_run(run)
        # Store task request for pipeline orchestration
        if request:
            request_path = self.repository.task_dir(task_id) / "request.json"
            request_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
            # 文案整理：auto-prepare script if present
            script_text = request.get("script", "").strip()
            if script_text:
                preparation = prepare_script(
                    script_text,
                    target_chars=request.get("target_chars", 80),
                    min_chars=request.get("min_chars", 35),
                    max_chars=request.get("max_chars", 140),
                )
                task_json_path = self.repository.task_dir(task_id) / "task.json"
                task_data = json.loads(task_json_path.read_text(encoding="utf-8"))
                task_data["script_preparation"] = preparation
                task_data["visual_anchor_enabled"] = request.get("visual_anchor_enabled", True)
                task_json_path.write_text(json.dumps(task_data, ensure_ascii=False, indent=2), encoding="utf-8")
        event = self.telemetry.append_event(task_id, run_id, {
            "event_type": "TaskCreated",
            "command": "task.create",
            "pipeline_id": pipeline_id,
            "engine": engine.value,
        })
        self.telemetry.append_audit(task_id, run_id, {
            "action": "task.create",
            "command_id": context.command_id,
            "entrypoint": context.entrypoint.value,
        })
        return self._ok("task.create", task, run, context, event_sequence=event["sequence"])

    def show_task(self, task_id: str) -> dict[str, Any]:
        task = self.repository.get_task(task_id)
        run = self.repository.get_run(task_id, task.active_run_id) if task.active_run_id else None
        return {"ok": True, "task": task.to_dict(), "active_run": run.to_dict() if run else None}

    def trace_run(self, task_id: str, run_id: str) -> dict[str, Any]:
        run = self.repository.get_run(task_id, run_id)
        return {"ok": True, "task_id": task_id, "run_id": run_id, "trace_id": run.trace_id, "command_ids": run.command_ids, "status": run.status.value}

    def list_events(self, task_id: str, run_id: str, after_sequence: int = 0) -> dict[str, Any]:
        events = self.telemetry.read_events(task_id, run_id, after_sequence)
        return {"ok": True, "task_id": task_id, "run_id": run_id, "items": events, "next_cursor": events[-1]["sequence"] if events else after_sequence}

    def list_logs(self, task_id: str, run_id: str) -> dict[str, Any]:
        path = self.repository.run_dir(task_id, run_id) / "observability" / "logs.jsonl"
        self.repository.get_run(task_id, run_id)
        items = [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        return {"ok": True, "task_id": task_id, "run_id": run_id, "items": items}

    def export_diagnostics(self, task_id: str, run_id: str) -> dict[str, Any]:
        path = self.telemetry.export_diagnostic_bundle(task_id, run_id)
        return {"ok": True, "task_id": task_id, "run_id": run_id, "bundle": str(path)}

    def generate_visual_anchors(self, task_id: str, run_id: str, context: CommandContext | None = None) -> dict[str, Any]:
        """Generate visual anchors for each saved Voice Unit.

        Reads script_preparation.voice_units from task.json — does NOT re-segment.
        If visual_anchor_enabled is false, writes default anchors (no LLM call).
        If visual_anchor_enabled is true, calls TextModel per unit for visual intent.
        """
        run = self.repository.get_run(task_id, run_id)
        task = self.repository.get_task(task_id)
        if task.pipeline_id != "mountain-av-v1":
            raise DomainError("VALIDATION_ERROR", "仅 mountain-av-v1 可运行 generate-visual-anchors")
        context = context or CommandContext(entrypoint=Entrypoint.CLI)

        # Read saved script_preparation from task.json
        task_json_path = self.repository.task_dir(task_id) / "task.json"
        task_data = json.loads(task_json_path.read_text(encoding="utf-8"))
        preparation = task_data.get("script_preparation")
        if not preparation or not preparation.get("voice_units"):
            raise DomainError("VALIDATION_ERROR", "请先保存文案并完成文案整理")
        saved_units = preparation["voice_units"]
        visual_anchor_enabled = task_data.get("visual_anchor_enabled", True)

        run.status = RunStatus.RUNNING
        warnings: list[str] = []

        # Build voice_units with visual_items for av-plan artifact
        voice_units_for_plan: list[dict[str, Any]] = []
        for unit in saved_units:
            unit_id = unit["unit_id"]
            source_range = unit["source_range"]

            if not visual_anchor_enabled:
                # Default anchor — no LLM call
                visual_items = [{
                    "visual_id": f"visual-{unit['order']:03d}-01",
                    "order": 1,
                    "source_range": source_range,
                    "text": unit["text"],
                    "anchor_text": unit["text"],
                    "highlight_text": "",
                    "visual_intent": "default",
                    "source": "default",
                }]
            else:
                # LLM anchor — call TextModel
                visual_items = self._generate_llm_anchors(
                    task_id, run_id, unit, context, warnings,
                )

            voice_units_for_plan.append({
                "unit_id": unit_id,
                "order": unit["order"],
                "source_range": source_range,
                "text": unit["text"],
                "visual_items": visual_items,
            })

        # Build and commit av-plan artifact
        source_text = preparation.get("source_text", "")
        document = {
            "schema_version": 1,
            "artifact_type": "av-plan",
            "task_id": task_id,
            "run_id": run_id,
            "pipeline_id": "mountain-av-v1",
            "engine": task.engine.value,
            "producer_stage": "generate-visual-anchors",
            "voice_units": voice_units_for_plan,
        }
        artifact = FilesystemArtifactStore(self.repository).commit_bytes(
            task_id, run_id, "planning.av-plan", "planning/av-plan.json",
            json_bytes(document), "generate-visual-anchors",
        )

        run.command_ids.append(context.command_id)
        run.stages["generate-visual-anchors"] = StageState(StageStatus.SUCCEEDED, 1)
        self.repository.save_run(run)

        event = self.telemetry.append_event(task_id, run_id, {
            "event_type": "VisualAnchorsGenerated",
            "unit_count": len(saved_units),
            "visual_anchor_enabled": visual_anchor_enabled,
        })
        self.telemetry.append_audit(task_id, run_id, {
            "action": "stage.run",
            "stage": "generate-visual-anchors",
            "command_id": context.command_id,
        })

        result_status = "succeeded"
        if not visual_anchor_enabled:
            result_status = "skipped"

        return {
            "ok": True, "command": "stage.run",
            "task_id": task_id, "run_id": run_id,
            "trace_id": run.trace_id, "command_id": context.command_id,
            "stage": "generate-visual-anchors", "result": result_status,
            "artifacts": [artifact.artifact_key],
            "event_sequence": event["sequence"],
            "warnings": warnings, "next_stage": "clone-voice",
        }

    def _generate_llm_anchors(
        self,
        task_id: str,
        run_id: str,
        unit: dict[str, Any],
        context: CommandContext,
        warnings: list[str],
    ) -> list[dict[str, Any]]:
        """Call TextModel to generate visual anchors for a single unit.

        Falls back to default anchors on LLM failure.
        """
        if self.provider_factory is None:
            warnings.append(f"{unit['unit_id']}: TextModel 不可用，使用默认锚定")
            self.telemetry.append_event(task_id, run_id, {
                "event_type": "VisualAnchorFallback",
                "unit_id": unit["unit_id"],
                "reason": "PROVIDER_NOT_AVAILABLE",
            })
            return [self._default_visual_item(unit)]

        try:
            if self.service_resolver is not None:
                text_def = self.service_resolver.resolve("text_generation")
                text_model = self.provider_factory.create_adapter(text_def)
            else:
                text_model = self.provider_factory.create_text()
        except Exception:
            warnings.append(f"{unit['unit_id']}: TextModel 创建失败，使用默认锚定")
            self.telemetry.append_event(task_id, run_id, {
                "event_type": "VisualAnchorFallback",
                "unit_id": unit["unit_id"],
                "reason": "TEXT_MODEL_CREATE_FAILED",
            })
            return [self._default_visual_item(unit)]

        prompt = (
            f"以下是视频旁白的一个段落：\n\n{unit['text']}\n\n"
            "请为这个段落生成画面锚定信息，返回 JSON：\n"
            '{"anchor_text": "核心旁白关键词", "highlight_text": "需要视觉强调的部分", '
            '"visual_intent": "画面描述意图"}\n'
            "只返回 JSON，不要其他内容。"
        )

        try:
            response = text_model.generate(prompt)
            import json as _json
            parsed = _json.loads(response)

            # Strict validation: unit_id must match, no new text/order/source_range changes
            anchor_text = str(parsed.get("anchor_text", ""))[:200]
            highlight_text = str(parsed.get("highlight_text", ""))[:200]
            visual_intent = str(parsed.get("visual_intent", ""))[:500]

            return [{
                "visual_id": f"visual-{unit['order']:03d}-01",
                "order": 1,
                "source_range": unit["source_range"],  # Must not change
                "text": unit["text"],  # Must not change
                "anchor_text": anchor_text,
                "highlight_text": highlight_text,
                "visual_intent": visual_intent,
                "source": "llm",
            }]
        except Exception as exc:
            warnings.append(f"{unit['unit_id']}: LLM 锚定失败 ({exc})，降级为默认")
            self.telemetry.append_event(task_id, run_id, {
                "event_type": "VisualAnchorFallback",
                "unit_id": unit["unit_id"],
                "reason": "LLM_OUTPUT_INVALID",
                "error": str(exc)[:200],
            })
            return [self._default_visual_item(unit)]

    @staticmethod
    def _default_visual_item(unit: dict[str, Any]) -> dict[str, Any]:
        return {
            "visual_id": f"visual-{unit['order']:03d}-01",
            "order": 1,
            "source_range": unit["source_range"],
            "text": unit["text"],
            "anchor_text": unit["text"],
            "highlight_text": "",
            "visual_intent": "default",
            "source": "default",
        }

    def clone_voice(
        self,
        task_id: str,
        run_id: str,
        tts: TextToSpeechPort,
        alignment: AlignmentPort,
        media: MediaPort,
        reference_audio: Path,
        unit_id: str | None = None,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        run = self.repository.get_run(task_id, run_id)
        task = self.repository.get_task(task_id)
        if task.pipeline_id != "mountain-av-v1":
            raise ValueError("仅 mountain-av-v1 可运行 clone-voice")

        # Read av-plan artifact to get voice units
        av_plan_ref = FilesystemArtifactStore(self.repository).get(task_id, run_id, "planning.av-plan")
        if not av_plan_ref:
            raise ValueError("请先运行 generate-visual-anchors 生成 av-plan")
        import json
        av_plan_path = self.repository.run_dir(task_id, run_id) / "artifacts" / av_plan_ref["relative_path"]
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
            task_id, run_id, tuple(units),
            profile="default", engine=task.engine,
        )

        event = self.telemetry.append_event(task_id, run_id, {
            "event_type": "CloneVoiceSucceeded",
            "unit_count": len(units),
        })
        self.telemetry.append_audit(task_id, run_id, {
            "action": "stage.run",
            "stage": "clone-voice",
            "command_id": context.command_id,
        })

        return {
            "ok": True,
            "command": "stage.run",
            "task_id": task_id,
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
        task_id: str,
        run_id: str,
        artifact_key: str,
    ) -> dict[str, Any]:
        """Return the content of an artifact by key."""
        self.repository.get_run(task_id, run_id)  # validate run exists
        store = FilesystemArtifactStore(self.repository)
        ref = store.get(task_id, run_id, artifact_key)
        if not ref:
            raise NotFoundError(f"Artifact {artifact_key} 不存在")
        run_dir = self.repository.run_dir(task_id, run_id)
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
            "task_id": task_id,
            "run_id": run_id,
            "artifact_key": artifact_key,
            "content": content,
            "metadata": ref,
        }

    def stage_retry(
        self,
        task_id: str,
        run_id: str,
        stage: str,
        unit_id: str | None = None,
        visual_id: str | None = None,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Retry a stage, optionally scoped to a specific unit or visual."""
        run = self.repository.get_run(task_id, run_id)
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

        self.telemetry.append_event(task_id, run_id, {
            "event_type": "StageRetryRequested",
            "stage": stage,
            "unit_id": unit_id,
            "visual_id": visual_id,
        })
        self.telemetry.append_audit(task_id, run_id, {
            "action": "stage.retry",
            "stage": stage,
            "command_id": context.command_id,
            "unit_id": unit_id,
            "visual_id": visual_id,
        })

        # Execute the stage via pipeline
        result = self.pipeline.run_pipeline(
            task_id, run_id,
            policy="targeted",
            target_stage=stage,
            context=context,
        )
        return result

    def pipeline_run(
        self,
        task_id: str,
        run_id: str | None = None,
        policy: str = "auto",
        target_stage: str | None = None,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Run the pipeline with the given policy."""
        task = self.repository.get_task(task_id)
        if run_id is None:
            run_id = task.active_run_id
        if not run_id:
            raise NotFoundError("任务没有活跃的运行")
        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        self.telemetry.append_audit(task_id, run_id, {
            "action": "pipeline.run",
            "policy": policy,
            "command_id": context.command_id,
        })
        return self.pipeline.run_pipeline(task_id, run_id, policy, target_stage, context)

    def pipeline_resume(
        self,
        task_id: str,
        run_id: str | None = None,
        policy: str = "auto",
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Resume a pipeline from the last successful stage."""
        task = self.repository.get_task(task_id)
        if run_id is None:
            run_id = task.active_run_id
        if not run_id:
            raise NotFoundError("任务没有活跃的运行")
        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        self.telemetry.append_audit(task_id, run_id, {
            "action": "pipeline.resume",
            "policy": policy,
            "command_id": context.command_id,
        })
        return self.pipeline.resume_pipeline(task_id, run_id, policy, context)

    # ── Stage executor wrappers ──────────────────────────────────────

    def _exec_generate_visual_anchors(self, task_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for generate-visual-anchors. Reads from task.json script_preparation."""
        return self.generate_visual_anchors(task_id, run_id, context)

    def _exec_clone_voice(self, task_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for clone-voice. Uses ServiceResolver + ProviderFactory.create_adapter."""
        if self.provider_factory is None:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", "ProviderFactory 未注入，无法构造 TTS/alignment/media adapter")

        request = self._read_request(task_id)
        reference_audio = request.get("reference_audio")
        if not reference_audio:
            raise DomainError("VALIDATION_ERROR", "任务请求中缺少 reference_audio 字段")

        # 解析相对路径：inputs/reference.wav → task_dir/inputs/reference.wav
        ref_path = Path(reference_audio)
        if not ref_path.is_absolute():
            ref_path = self.repository.task_dir(task_id) / ref_path
        if not ref_path.exists():
            raise DomainError("VALIDATION_ERROR", f"参考音频文件不存在: {reference_audio}")

        # 动态解析：speech_synthesis + speech_alignment
        if self.service_resolver is not None:
            tts_def = self.service_resolver.resolve("speech_synthesis")
            tts = self.provider_factory.create_adapter(tts_def)
            alignment_def = self.service_resolver.resolve("speech_alignment")
            alignment = self.provider_factory.create_adapter(alignment_def)
            media_def = self.service_resolver.resolve("media")
            media = self.provider_factory.create_adapter(media_def)
        else:
            # 回退：旧固定路径（CLI 兼容）
            tts = self.provider_factory.create_tts()
            alignment = self.provider_factory.create_alignment()
            media = self.provider_factory.create_media()

        return self.clone_voice(
            task_id, run_id, tts, alignment, media,
            reference_audio=ref_path,
            context=context,
        )

    def _read_request(self, task_id: str) -> dict[str, Any]:
        """Read the task request.json if it exists."""
        request_path = self.repository.task_dir(task_id) / "request.json"
        if request_path.exists():
            return json.loads(request_path.read_text(encoding="utf-8"))
        return {}

    def plan_storyboard(
        self,
        task_id: str,
        run_id: str,
        text_model: TextModelPort,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Generate storyboard for all Visual Items."""
        run = self.repository.get_run(task_id, run_id)
        task = self.repository.get_task(task_id)
        context = context or CommandContext(entrypoint=Entrypoint.CLI)

        run.status = RunStatus.RUNNING
        run.stages["plan-storyboard"] = StageState(StageStatus.RUNNING, 1)
        run.command_ids.append(context.command_id)
        self.repository.save_run(run)

        service = StoryboardService(text_model, self.repository)
        result = service.run(task_id, run_id, task.engine)

        run.stages["plan-storyboard"] = StageState(StageStatus.SUCCEEDED, 1)
        self.repository.save_run(run)

        event = self.telemetry.append_event(task_id, run_id, {
            "event_type": "StoryboardGenerated",
            "visual_count": result["visual_count"],
        })
        self.telemetry.append_audit(task_id, run_id, {
            "action": "stage.run",
            "stage": "plan-storyboard",
            "command_id": context.command_id,
        })

        return {
            "ok": True,
            "command": "stage.run",
            "task_id": task_id,
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
        task_id: str,
        run_id: str,
        image_model: ImageModelPort,
        visual_id: str | None = None,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Generate illustrations for Visual Items."""
        run = self.repository.get_run(task_id, run_id)
        task = self.repository.get_task(task_id)
        context = context or CommandContext(entrypoint=Entrypoint.CLI)

        run.status = RunStatus.RUNNING
        run.stages["generate-illustrations"] = StageState(StageStatus.RUNNING, 1)
        run.command_ids.append(context.command_id)
        self.repository.save_run(run)

        service = IllustrationService(image_model, self.repository)
        result = service.run(task_id, run_id, task.engine, visual_id)

        run.stages["generate-illustrations"] = StageState(StageStatus.SUCCEEDED, 1)
        self.repository.save_run(run)

        event = self.telemetry.append_event(task_id, run_id, {
            "event_type": "IllustrationsGenerated",
            "image_count": result["image_count"],
        })
        self.telemetry.append_audit(task_id, run_id, {
            "action": "stage.run",
            "stage": "generate-illustrations",
            "command_id": context.command_id,
        })

        return {
            "ok": True,
            "command": "stage.run",
            "task_id": task_id,
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

    def _exec_plan_storyboard(self, task_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for plan-storyboard. Uses ServiceResolver + ProviderFactory.create_adapter."""
        if self.provider_factory is None:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", "ProviderFactory 未注入，无法构造 text model")
        if self.service_resolver is not None:
            text_def = self.service_resolver.resolve("text_generation")
            text_model = self.provider_factory.create_adapter(text_def)
        else:
            text_model = self.provider_factory.create_text_model()
        return self.plan_storyboard(task_id, run_id, text_model, context)

    def _exec_generate_illustrations(self, task_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for generate-illustrations. Uses ServiceResolver + ProviderFactory.create_adapter."""
        if self.provider_factory is None:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", "ProviderFactory 未注入，无法构造 image model")
        if self.service_resolver is not None:
            image_def = self.service_resolver.resolve("image_generation")
            image_model = self.provider_factory.create_adapter(image_def)
        else:
            image_model = self.provider_factory.create_image_model()
        return self.generate_illustrations(task_id, run_id, image_model, context=context)

    def render_visuals(
        self,
        task_id: str,
        run_id: str,
        renderer: RendererPort,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Render video clips for all Visual Items."""
        from csboard.application.av_artifacts import read_manifest
        from csboard.domain.provider_types import RenderRequest

        run = self.repository.get_run(task_id, run_id)
        task = self.repository.get_task(task_id)
        context = context or CommandContext(entrypoint=Entrypoint.CLI)

        run.status = RunStatus.RUNNING
        run.stages["render-visuals"] = StageState(StageStatus.RUNNING, 1)
        run.command_ids.append(context.command_id)
        self.repository.save_run(run)

        run_dir = self.repository.run_dir(task_id, run_id)
        store = FilesystemArtifactStore(self.repository)
        def artifact_path(key: str) -> Path | None:
            ref = store.get(task_id, run_id, key)
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
            request_id=f"{task_id}:{run_id}:render",
        )

        # Execute render
        result = renderer.render(request)

        # Build render manifest
        render_manifest = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "engine": task.engine.value,
            "total_duration_ms": result.duration_ms,
            "total_frames": result.frames,
            "clips": result.provider_metadata.get("clips", []),
            "output_path": str(result.output_path.relative_to(self.repository.root)),
        }

        artifact_key = store.commit_bytes(
            task_id, run_id, "render.manifest", "render/render-manifest.json",
            json_bytes(render_manifest), "render-visuals",
        ).artifact_key

        run.stages["render-visuals"] = StageState(StageStatus.SUCCEEDED, 1)
        self.repository.save_run(run)

        event = self.telemetry.append_event(task_id, run_id, {
            "event_type": "RenderCompleted",
            "clip_count": len(render_manifest.get("clips", [])),
            "total_duration_ms": result.duration_ms,
        })
        self.telemetry.append_audit(task_id, run_id, {
            "action": "stage.run",
            "stage": "render-visuals",
            "command_id": context.command_id,
        })

        return {
            "ok": True,
            "command": "stage.run",
            "task_id": task_id,
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
        task_id: str,
        run_id: str,
        media: MediaPort,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Compose final video from rendered clips and audio."""
        run = self.repository.get_run(task_id, run_id)
        task = self.repository.get_task(task_id)
        context = context or CommandContext(entrypoint=Entrypoint.CLI)

        run.status = RunStatus.RUNNING
        run.stages["compose-video"] = StageState(StageStatus.RUNNING, 1)
        run.command_ids.append(context.command_id)
        self.repository.save_run(run)

        service = CompositionService(media, self.repository)
        result = service.run(task_id, run_id)

        run.stages["compose-video"] = StageState(StageStatus.SUCCEEDED, 1)
        run.status = RunStatus.SUCCEEDED
        self.repository.save_run(run)

        event = self.telemetry.append_event(task_id, run_id, {
            "event_type": "CompositionCompleted",
            "output_path": result["output_path"],
            "duration_ms": result["duration_ms"],
        })
        self.telemetry.append_audit(task_id, run_id, {
            "action": "stage.run",
            "stage": "compose-video",
            "command_id": context.command_id,
        })

        return {
            "ok": True,
            "command": "stage.run",
            "task_id": task_id,
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

    def _exec_render_visuals(self, task_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for render-visuals. Uses ServiceResolver + ProviderFactory.create_adapter."""
        if self.provider_factory is None:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", "ProviderFactory 未注入，无法构造 renderer")
        if self.service_resolver is not None:
            render_def = self.service_resolver.resolve("rendering")
            renderer = self.provider_factory.create_adapter(render_def)
        else:
            renderer = self.provider_factory.create_renderer()
        return self.render_visuals(task_id, run_id, renderer, context)

    def _exec_compose_video(self, task_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for compose-video. Uses ServiceResolver + ProviderFactory.create_adapter."""
        if self.provider_factory is None:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", "ProviderFactory 未注入，无法构造 media adapter")
        if self.service_resolver is not None:
            media_def = self.service_resolver.resolve("media")
            media = self.provider_factory.create_adapter(media_def)
        else:
            media = self.provider_factory.create_media()
        return self.compose_video(task_id, run_id, media, context)

    @staticmethod
    def _ok(command: str, task: Task, run: Run, context: CommandContext, **extra: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "command": command,
            "task_id": task.task_id,
            "run_id": run.run_id,
            "trace_id": run.trace_id,
            "command_id": context.command_id,
            **extra,
        }
