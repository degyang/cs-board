from __future__ import annotations

import json
from copy import deepcopy
import hashlib
import re
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from csboard.adapters.filesystem import FilesystemTaskRepository
from csboard.adapters.filesystem import FilesystemArtifactStore
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.av_artifacts import av_plan_document, json_bytes, render_manifest_document
from csboard.application.composition import CompositionService
from csboard.application.context import CommandContext, new_id, utc_now
from csboard.application.illustrations import IllustrationService
from csboard.application.illustration_candidates import IllustrationCandidateService
from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
from csboard.application.pipeline import PipelineOrchestrator
from csboard.application.storyboard import StoryboardService
from csboard.application.voice_units import VoiceUnitService
from csboard.application.work_orders import WorkOrderService
from csboard.domain.av_timing import VoiceUnit, segment_script
from csboard.domain.script_preparation import prepare_script
from csboard.domain.enums import Engine, Entrypoint, TaskStatus, RunStatus, StageStatus
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.models import Task, Run, StageState
from csboard.domain.execution_plan import ExecutionPlan, CANONICAL_STAGES
from csboard.domain.stage_gate import StageGate, GATE_APPROVED, GATE_WAITING, GATE_REJECTED, GATE_REDO
from csboard.ports.providers import AlignmentPort, ImageModelPort, MediaPort, RendererPort, TextModelPort, TextToSpeechPort


UPLOAD_REFERENCE_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
ALLOWED_LINE_DENSITY = ("minimal", "standard", "rich", "complete")
LINE_DENSITY_TO_STROKE = {
    "minimal": "light",
    "standard": "standard",
    "rich": "detailed",
    "complete": "full",
}
STYLE_DEFAULTS = {
    "target_chars": 45,
    "shots_per_image": 2,
    "line_density": "rich",
    "visual_anchor_enabled": True,
    "include_subtitles": True,
}


def _is_high_entropy_token(value: str) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) < 16:
        return False
    if not re.search(r"[A-Za-z]", value) or not re.search(r"[0-9]", value):
        return False
    # 约束重复字符比例，避免弱 token
    ratio = len(set(value)) / len(value)
    return ratio >= 0.45


def _derive_script_rules(target_chars: int) -> tuple[int, int]:
    target = max(5, min(500, target_chars))
    min_chars = max(5, int(target * 0.6))
    max_chars = min(500, max(target * 2, target + 40))
    return min_chars, max_chars



@dataclass(slots=True)
class MountainCommands:
    """Entry-point-neutral commands used by CLI now and Web/Skills later.

    service_resolver: 动态服务解析器（用于获取 ServiceDefinition）
    provider_factory: 适配器工厂（用于 create_adapter(service_definition)）
    repository: 可选注入的 TaskRepository（组合根创建后注入）
    telemetry: 可选注入的 Telemetry（组合根创建后注入）
    """

    root: Path
    provider_factory: Any | None = None  # ProviderFactory for real adapters
    service_resolver: Any | None = None  # ServiceResolver for dynamic resolution
    repository: FilesystemTaskRepository | None = None  # 注入的 repository
    telemetry: JsonlTelemetry | None = None  # 注入的 telemetry
    asset_repository: FilesystemAssetRepository | None = None
    # P4's only allowed infographic execution seam.  Production composition
    # does not expose it through HTTP/CLI; fake E2E injects a test renderer.
    infographic_renderer_factory: Any | None = None
    pipeline: PipelineOrchestrator = field(init=False)

    def __post_init__(self) -> None:
        if self.repository is None:
            self.repository = FilesystemTaskRepository(self.root)
        if self.asset_repository is None:
            self.asset_repository = FilesystemAssetRepository(self.root)
        if self.telemetry is None:
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
        *,
        summary: str | None = None,
        submission_id: str | None = None,
        internal_test_only: bool = False,
    ) -> dict[str, Any]:
        if not title.strip():
            raise ValueError("任务名称不能为空")
        # Older CLI callers did not have a summary field.  The HTTP boundary
        # requires it, while this fallback preserves existing local commands.
        resolved_summary = title.strip() if summary is None else summary.strip()
        if not resolved_summary:
            raise ValueError("任务摘要不能为空")
        if pipeline_id != "mountain-av-v1":
            raise ValueError("仅支持 mountain-av-v1 流水线")
        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        if engine is Engine.INFOGRAPHIC_REMOTION:
            from csboard.application.capabilities import CapabilityService
            cap_svc = CapabilityService(
                self.service_resolver._registry, project_root=self.root,
            ) if self.service_resolver is not None else None
            # P4 is intentionally not a public submission switch.  A caller
            # must opt in at this non-HTTP seam *and* carry the test actor.
            if cap_svc is None:
                raise DomainError("CAPABILITY_NOT_AVAILABLE", "引擎 infographic-remotion 当前不可用")
            cap_snapshot = cap_svc.snapshot()
            infographic_item = next(
                (item for item in cap_snapshot["items"]
                 if item["engine"] == "infographic-remotion"
                 and item["visual_source"] == "preset"),
                None,
            )
            # P3a remains publicly unsupported.  P4 consumes bootstrap only
            # for its controlled fake/internal route; P2 is bound by the
            # concrete adapter selected below, never by generic rendering.
            internal_allowed = internal_test_only and context.actor_type == "internal-test" and bool((infographic_item or {}).get("bootstrap_ready"))
            if infographic_item is None or not internal_allowed:
                reason = (infographic_item or {}).get("reason_code") or "CAPABILITY_NOT_AVAILABLE"
                raise DomainError("CAPABILITY_NOT_AVAILABLE", f"引擎 infographic-remotion 当前不可用: {reason}")
        if submission_id is not None and not _is_high_entropy_token(submission_id):
            raise ValueError("submission_id 必须是高熵客户端标识")
        output_root = None if request is None else request.get("output_root")
        # The root is a placement instruction, not task-package content: an
        # absolute machine path must never leak into a portable package.
        persisted_request = None if request is None else {key: value for key, value in request.items() if key != "output_root"}
        resolved_output_root = self.repository.resolve_output_root(output_root)
        task_id = new_id("task")
        run_id = new_id("run")
        trace_id = new_id("trace")
        task = Task(
            task_id=task_id,
            title=title.strip()[:80],
            summary=resolved_summary[:240],
            pipeline_id=pipeline_id,
            engine=engine,
            status=TaskStatus.READY,
            created_at=utc_now(),
            updated_at=utc_now(),
            active_run_id=run_id,
            submission_id=submission_id,
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
        if submission_id:
            signature = hashlib.sha256(json.dumps({
                "title": task.title,
                "summary": task.summary,
                "pipeline_id": pipeline_id,
                "engine": engine.value,
                "output_root": str(resolved_output_root),
            }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            created = self.repository.create_task_submission(
                submission_id, task, run, signature, created_at=task.created_at,
                output_root=output_root,
            )
            if created["task_id"] != task_id:
                task = self.repository.get_task(created["task_id"])
                run = self.repository.get_run(task.task_id, created["run_id"])
                return self._ok("task.create", task, run, context)
        else:
            self.repository.create_task(task, output_root=output_root)
            self.repository.create_run(run)
        # Store task request for pipeline orchestration
        if persisted_request:
            self.repository.write_json(self.repository.task_dir(task_id) / "request.json", persisted_request)
            # 文案整理：auto-prepare script if present
            script_text = persisted_request.get("script", "")
            if script_text.strip():
                preparation = prepare_script(
                    script_text,
                    target_chars=persisted_request.get("target_chars", 80),
                    min_chars=persisted_request.get("min_chars", 35),
                    max_chars=persisted_request.get("max_chars", 140),
                )
                task_json_path = self.repository.task_dir(task_id) / "task.json"
                task_data = json.loads(task_json_path.read_text(encoding="utf-8"))
                task_data["script_preparation"] = preparation
                task_data["visual_anchor_enabled"] = persisted_request.get("visual_anchor_enabled", True)
                self.repository.write_json(task_json_path, task_data)
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

    def create_options(self) -> dict[str, Any]:
        """Authoritative six-tab capability query used by every delivery edge."""
        engines: list[dict[str, Any]] = [
            {"id": "whiteboard", "label": "白板动画", "available": True},
        ]

        # Infographic-remotion: dynamically check capability from the service
        # registry and remotion toolchain readiness.
        if self.service_resolver is not None:
            from csboard.application.capabilities import CapabilityService
            cap_svc = CapabilityService(
                self.service_resolver._registry, project_root=self.root,
            )
            cap_snapshot = cap_svc.snapshot()
            infographic_item = next(
                (item for item in cap_snapshot["items"]
                 if item["engine"] == "infographic-remotion"
                 and item["visual_source"] == "preset"),
                None,
            )
            if infographic_item is not None:
                engines.append({
                    "id": "infographic-remotion",
                    "label": "动态信息图",
                    "available": infographic_item["supported"],
                    "reason": infographic_item.get("reason_code") or "能力未就绪",
                })
        else:
            engines.append({
                "id": "infographic-remotion",
                "label": "动态信息图",
                "available": False,
                "reason": "CAPABILITY_NOT_AVAILABLE",
            })

        return {
            "engines": engines,
            "visual_sources": [
                {"id": "preset", "label": "预设风格", "available": True},
                {"id": "custom-reference", "label": "自定义参考", "available": True},
            ],
            "voice_sources": [
                {"id": "voice-asset", "label": "音色资产", "available": True},
                {"id": "uploaded-reference", "label": "上传参考音频", "available": True},
            ],
            "limits": {"script_min_chars": 10, "target_chars_min": 5, "target_chars_max": 500, "brand_text_max_chars": 12},
            "defaults": {"engine": "whiteboard", "visual_source": "preset", **STYLE_DEFAULTS},
        }

    def preview_script(self, script: str, target_chars: int = STYLE_DEFAULTS["target_chars"]) -> dict[str, Any]:
        """Compute the read-only authoritative preview; no task is created."""
        if not 5 <= target_chars <= 500:
            raise DomainError("VALIDATION_ERROR", "target_chars 必须为 5–500")
        min_chars, max_chars = _derive_script_rules(target_chars)
        try:
            return prepare_script(script, target_chars=target_chars, min_chars=min_chars, max_chars=max_chars)
        except ValueError as exc:
            raise DomainError("VALIDATION_ERROR", str(exc)) from exc

    def show_task(self, task_id: str) -> dict[str, Any]:
        task = self.repository.get_task(task_id)
        run = self.repository.get_run(task_id, task.active_run_id) if task.active_run_id else None
        request = self.repository.get_request(task_id) or {}
        plan = ExecutionPlan.from_dict(request.get("execution_plan", {}))
        result = {"ok": True, "task": task.to_dict(), "active_run": run.to_dict() if run else None, "execution_plan": plan.to_dict()}
        recovery = self.repository.recovery_metadata(task_id)
        if recovery:
            result["recovery_status"] = "partial"
            result["recovery"] = recovery
        return result

    def list_tasks(
        self,
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        q: str | None = None,
    ) -> dict[str, Any]:
        """列出任务：filter → sort → cursor → limit。"""
        # 1. 读取所有 task
        all_tasks = []
        for task_id in self.repository.list_task_ids():
            try:
                task = self.repository.get_task(task_id)
                all_tasks.append(task)
            except (NotFoundError, Exception):
                continue

        # 2. filter (status, q)
        filtered = []
        for task in all_tasks:
            td = task.to_dict()
            if status and td.get("status") != status:
                continue
            if q:
                q_lower = q.lower()
                title_match = q_lower in td.get("title", "").lower()
                id_match = q_lower in td.get("task_id", "").lower()
                if not title_match and not id_match:
                    continue
            filtered.append(task)

        # 3. sort (running first, failed second, then updated_at DESC)
        _PRIORITY = {"running": 0, "failed": 1}

        def _sort_key(task):
            td = task.to_dict()
            priority = _PRIORITY.get(td.get("status", "draft"), 2)
            return (priority, td.get("updated_at", ""))

        filtered.sort(key=_sort_key, reverse=True)

        # 4. cursor
        if cursor:
            cursor_idx = -1
            for idx, task in enumerate(filtered):
                if task.task_id == cursor:
                    cursor_idx = idx + 1
                    break
            if cursor_idx > 0:
                filtered = filtered[cursor_idx:]

        # 5. limit
        effective_limit = max(1, min(limit, 100))
        page = filtered[:effective_limit]

        # 6. build items
        items = []
        for task in page:
            td = task.to_dict()
            active_run = None
            if task.active_run_id:
                try:
                    run = self.repository.get_run(task.task_id, task.active_run_id)
                    current_stage = None
                    for stage_name in reversed(["generate-visual-anchors", "clone-voice", "plan-storyboard", "generate-illustrations", "render-visuals", "compose-video"]):
                        stage_state = run.stages.get(stage_name)
                        if stage_state and stage_state.status in (StageStatus.RUNNING, StageStatus.FAILED):
                            current_stage = stage_name
                            break
                        if stage_state and stage_state.status == StageStatus.SUCCEEDED:
                            break
                    if current_stage is None and run.status == RunStatus.RUNNING:
                        for stage_name in ["generate-visual-anchors", "clone-voice", "plan-storyboard", "generate-illustrations", "render-visuals", "compose-video"]:
                            stage_state = run.stages.get(stage_name)
                            if not stage_state or stage_state.status == StageStatus.PENDING:
                                current_stage = stage_name
                                break
                    active_run = {
                        "run_id": run.run_id,
                        "status": run.status.value,
                        "current_stage": current_stage,
                        "started_at": run.started_at,
                        "retryable": run.status == RunStatus.FAILED,
                        "error_code": getattr(run, 'error_code', None),
                    }
                except NotFoundError:
                    pass
            td.pop("script_preparation", None)
            td.pop("visual_anchor_enabled", None)
            td["active_run"] = active_run
            recovery = self.repository.recovery_metadata(task.task_id)
            if recovery:
                td["recovery_status"] = "partial"
                td["recovery"] = recovery
            items.append(td)

        next_cursor = items[-1]["task_id"] if len(items) >= effective_limit else None
        return {"items": items, "next_cursor": next_cursor}

    def save_inputs(
        self,
        task_id: str,
        script: str,
        txn_dir: Path,
        reference_audio_filename: str | None = None,
        style: str = "极简粗线简笔白板风",
        include_subtitles: bool = True,
        pen_text: str = "",
        stroke_detail: str = "detailed",
        target_chars: int = 80,
        min_chars: int = 35,
        max_chars: int = 140,
        visual_anchor_enabled: bool = True,
        execution_mode: str = "auto",
        manual_stages: list[str] | None = None,
        context: CommandContext | None = None,
        *,
        voice_source: str | None = None,
        visual_source: str | None = None,
        style_asset_id: str | None = None,
        voice_asset_id: str | None = None,
        style_asset_revision: int | None = None,
        voice_asset_revision: int | None = None,
        style_revision: int | None = None,
        voice_revision: int | None = None,
        shots_per_image: int | None = None,
        line_density: str | None = None,
        brand_text: str | None = None,
    ) -> dict[str, Any]:
        """保存任务输入：通过 Application command 和 Repository 接口。

        接收事务目录（由 Repository 创建），在验证完成后原子提交。
        所有保存（有无 reference）都走同一事务。
        """
        # 验证任务存在
        self.repository.get_task(task_id)

        if len(script.strip()) < 10:
            raise DomainError("VALIDATION_ERROR", "文案至少需要 10 个字")

        formal_request = any(value is not None for value in (
            voice_source, visual_source, style_asset_id, voice_asset_id,
            style_asset_revision, voice_asset_revision, shots_per_image, line_density, brand_text,
        ))
        if style_asset_revision is None:
            style_asset_revision = style_revision
        if voice_asset_revision is None:
            voice_asset_revision = voice_revision
        style_template = None
        voice_asset = None
        if formal_request:
            if voice_source not in {"uploaded-reference", "voice-asset"} or visual_source not in {"preset", "custom-reference"}:
                raise DomainError("CAPABILITY_NOT_AVAILABLE", "当前组合暂不可用")
            if visual_source == "custom-reference" and not style_asset_id:
                raise DomainError("VALIDATION_ERROR", "style_asset_id 不能为空")
            if voice_source == "voice-asset" and not voice_asset_id:
                raise DomainError("VALIDATION_ERROR", "voice_asset_id 不能为空")
            if voice_source == "voice-asset" and reference_audio_filename is not None:
                raise DomainError("VALIDATION_ERROR", "voice-asset 不接受上传参考音频")
            if voice_source == "uploaded-reference" and voice_asset_id:
                raise DomainError("VALIDATION_ERROR", "uploaded-reference 不接受 voice_asset_id")
            if voice_source == "uploaded-reference" and reference_audio_filename is None:
                current = self.repository.get_request(task_id) or {}
                if not current.get("reference_audio"):
                    raise DomainError("VALIDATION_ERROR", "首次保存必须上传参考音频")
            if shots_per_image not in {1, 2, 3, 4}:
                raise DomainError("VALIDATION_ERROR", "shots_per_image 必须为 1–4")
            if line_density not in ALLOWED_LINE_DENSITY:
                raise DomainError("VALIDATION_ERROR", "line_density 不受支持")
            if brand_text is None or len(brand_text) > 12:
                raise DomainError("VALIDATION_ERROR", "brand_text 最长 12 个字符")
            if not 5 <= target_chars <= 500:
                raise DomainError("VALIDATION_ERROR", "target_chars 必须为 5–500")
            if style_asset_id:
                try:
                    style_template = self.asset_repository.get_style_template(style_asset_id)
                except (DomainError, NotFoundError):
                    raise DomainError("VALIDATION_ERROR", "style_asset_id 不存在或不可用")
                required_kind = "custom" if visual_source == "custom-reference" else "preset"
                if style_template.kind != required_kind or style_template.status != "active":
                    raise DomainError("VALIDATION_ERROR", "style_asset_id 不存在或不可用")
                if style_asset_revision is not None and style_asset_revision != style_template.revision:
                    raise DomainError("REVISION_CONFLICT", "风格资产版本已变化")
            if voice_asset_id:
                try:
                    voice_asset = self.asset_repository.get_voice_asset(voice_asset_id)
                except (DomainError, NotFoundError):
                    raise DomainError("VALIDATION_ERROR", "voice_asset_id 不存在或不可用")
                if not voice_asset.is_active:
                    raise DomainError("VALIDATION_ERROR", "voice_asset_id 不存在或不可用")
                if voice_asset_revision is not None and voice_asset_revision != voice_asset.revision:
                    raise DomainError("REVISION_CONFLICT", "音色资产版本已变化")

        # 验证音频文件（如果有）
        if reference_audio_filename:
            suffix = Path(reference_audio_filename).suffix.lower() or ".wav"
            staging_ref = txn_dir / f"reference{suffix}"
            if not staging_ref.exists():
                raise DomainError("VALIDATION_ERROR", "staging 文件不存在")
            if staging_ref.stat().st_size == 0:
                raise DomainError("VALIDATION_ERROR", "参考音频文件为空")
            if suffix not in {".wav", ".mp3", ".m4a", ".ogg", ".flac"}:
                raise DomainError("VALIDATION_ERROR", "参考音频格式不支持")

        # New six-tab requests derive compatibility rules deterministically.
        if formal_request:
            min_chars, max_chars = _derive_script_rules(target_chars)
            style = style_template.name if style_template else style
            pen_text = brand_text or ""
            stroke_detail = LINE_DENSITY_TO_STROKE[line_density or "rich"]
        execution_plan = None if formal_request else ExecutionPlan.create(
            execution_mode, [] if manual_stages is None else manual_stages,
        )
        try:
            preparation = prepare_script(
                script,
                target_chars=target_chars,
                min_chars=min_chars,
                max_chars=max_chars,
            )
        except ValueError as exc:
            raise DomainError("VALIDATION_ERROR", str(exc))

        # 所有验证通过，执行原子提交
        reference_audio_relative = None
        if reference_audio_filename:
            suffix = Path(reference_audio_filename).suffix.lower() or ".wav"
            reference_audio_relative = f"inputs/reference{suffix}"

        request_data = {
            # Persist and segment the exact submitted source.  Validation above
            # still ignores surrounding whitespace when judging whether there is
            # enough content, but source ranges must be able to cover it.
            "script": script,
            "raw_script": script,
            "reference_audio": reference_audio_relative,
            "style": style,
            "include_subtitles": include_subtitles,
            "pen_text": pen_text[:12],
            "stroke_detail": stroke_detail if stroke_detail in {"light", "standard", "detailed", "full"} else "detailed",
            "target_chars": target_chars,
            "min_chars": min_chars,
            "max_chars": max_chars,
            "visual_anchor_enabled": visual_anchor_enabled,
        }
        if execution_plan is not None:
            request_data["execution_plan"] = execution_plan.to_dict()
        if formal_request:
            request_data.update({
                "voice_source": voice_source,
                "visual_source": visual_source,
                "style_asset_id": style_asset_id,
                "style_snapshot": ({
                    "style_id": style_template.style_id,
                    "revision": style_template.revision,
                    "name": style_template.name,
                    "prompt_text": style_template.prompt_text,
                    "negative_prompt": style_template.negative_prompt,
                    "config": deepcopy(style_template.config),
                } if style_template else None),
                "voice_asset_id": voice_asset_id,
                "voice_snapshot": ({
                    "voice_id": voice_asset.voice_id,
                    "revision": voice_asset.revision,
                    "name": voice_asset.name,
                    "language": voice_asset.language,
                    "emotion_mode": voice_asset.emotion_mode,
                    "emotion_weight": voice_asset.emotion_weight,
                    "engine": voice_asset.engine,
                    "compatibility": deepcopy(voice_asset.compatibility),
                } if voice_asset else None),
                "shots_per_image": shots_per_image,
                "line_density": line_density,
                "brand_text": brand_text,
            })

        # 原子提交：request + task preparation + reference
        # preserve_reference=True 时在 Repository 锁内从当前已提交状态保留 reference
        try:
            self.repository.commit_inputs(
                task_id=task_id,
                txn_dir=txn_dir,
                request_data=request_data,
                preparation=preparation,
                visual_anchor_enabled=visual_anchor_enabled,
                reference_filename=reference_audio_filename,
                preserve_reference=(reference_audio_filename is None),
                execution_plan=execution_plan.to_dict() if execution_plan else None,
            )
        except Exception as exc:
            # 不暴露绝对路径或异常原文
            raise DomainError("INTERNAL_ERROR", "输入提交失败")

        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        task = self.repository.get_task(task_id)
        run_id = task.active_run_id or ""
        if run_id:
            self.telemetry.append_event(task_id, run_id, {
                "event_type": "InputsSaved",
                "command": "task.save_inputs",
            })

        result = {
            "ok": True,
            "task_id": task_id,
            "input_saved": True,
        }
        if execution_plan is not None:
            result["execution_plan"] = execution_plan.to_dict()
        return result

    def get_inputs(self, task_id: str) -> dict[str, Any]:
        """读取已保存的任务输入。"""
        self.repository.get_task(task_id)  # validate task exists

        request_data = self.repository.get_request(task_id)
        if not request_data:
            return {
                "task_id": task_id,
                "saved": False,
                "inputs": None,
                "reference_audio": {"uploaded": False, "filename": None, "content_type": None, "size_bytes": None},
                "execution_plan": ExecutionPlan().to_dict(),
            }

        # 从 request.json 读取 reference 元数据（不扫描目录）
        audio_meta: dict[str, Any] = {"uploaded": False, "filename": None, "content_type": None, "size_bytes": None}
        reference_audio = request_data.get("reference_audio")
        if reference_audio:
            # 从相对路径读取元数据
            ref_path = self.repository.task_dir(task_id) / reference_audio
            if ref_path.exists():
                audio_meta = {
                    "uploaded": True,
                    "filename": ref_path.name,
                    "content_type": f"audio/{ref_path.suffix.lstrip('.')}",
                    "size_bytes": ref_path.stat().st_size,
                }

        # Task is a stable domain DTO and intentionally ignores unknown JSON
        # fields.  Input preparation is persisted alongside it, so read the
        # stored document here rather than serializing the DTO back again.
        task_data = self.repository.read_json(self.repository.task_dir(task_id) / "task.json")
        preparation = task_data.get("script_preparation")
        visual_anchor_enabled = task_data.get("visual_anchor_enabled", True)

        result = {
            "task_id": task_id,
            "saved": True,
            "inputs": {
                "script": request_data.get("raw_script", request_data.get("script", "")),
                "voice_source": request_data.get("voice_source", "uploaded-reference"),
                "visual_source": request_data.get("visual_source", "preset"),
                "style_asset_id": request_data.get("style_asset_id"),
                "voice_asset_id": request_data.get("voice_asset_id"),
                "style_snapshot": request_data.get("style_snapshot"),
                "voice_snapshot": request_data.get("voice_snapshot"),
                "shots_per_image": request_data.get("shots_per_image", 1),
                "line_density": request_data.get("line_density", "rich"),
                "brand_text": request_data.get("brand_text", request_data.get("pen_text", "")),
                "style": request_data.get("style", "极简粗线简笔白板风"),
                "include_subtitles": request_data.get("include_subtitles", True),
                "pen_text": request_data.get("pen_text", ""),
                "stroke_detail": request_data.get("stroke_detail", "detailed"),
            },
            "reference_audio": audio_meta,
            "rules": {
                "target_chars": request_data.get("target_chars", 80),
                "min_chars": request_data.get("min_chars", 35),
                "max_chars": request_data.get("max_chars", 140),
            },
            "script_preparation": preparation,
            "raw_script": request_data.get("raw_script", request_data.get("script", "")),
            "visual_anchor_enabled": visual_anchor_enabled,
        }
        if "execution_plan" in request_data:
            result["execution_plan"] = ExecutionPlan.from_dict(request_data["execution_plan"]).to_dict()
        elif "style_asset_id" not in request_data:
            # Old saved requests predate persisted plans.  Surface their
            # historic default without writing a migration during a read.
            result["execution_plan"] = ExecutionPlan().to_dict()
        return result

    def start_run(
        self,
        task_id: str,
        run_id: str,
        policy: str = "auto",
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """启动运行：检查输入和服务可用性。"""
        task = self.repository.get_task(task_id)
        self._require_native_task(task)
        run = self.repository.get_run(task_id, run_id)
        if run.task_id != task.task_id:
            raise NotFoundError("运行记录不存在")
        request_data = self.repository.get_request(task_id)
        self._validate_start_inputs(task_id, request_data)

        return {"ok": True, "state": "waiting-manual-trigger", "task_id": task_id,
                "run_id": run_id, "trace_id": run.trace_id,
                "next_stage": self.pipeline.get_next_stage(run),
                "gates": self.list_gates(task_id, run_id)["items"]}

    def _validate_start_inputs(self, task_id: str, request: dict[str, Any] | None) -> None:
        """Validate the persisted, non-negotiable manual-path inputs safely."""
        invalid: list[str] = []
        if not request or not isinstance(request.get("script"), str) or len(request["script"].strip()) < 10:
            invalid.append("script")
        if request and request.get("voice_source") == "voice-asset":
            snapshot = request.get("voice_snapshot")
            if not isinstance(snapshot, dict) or not snapshot.get("voice_id"):
                invalid.append("voice_asset_id")
            else:
                try:
                    self.asset_repository.get_voice_content(str(snapshot["voice_id"]))
                except (NotFoundError, DomainError):
                    invalid.append("voice_asset_id")
            reference = "voice-asset"
        else:
            reference = request.get("reference_audio") if request else None
        if request and request.get("voice_source") == "voice-asset":
            reference = "voice-asset"
        elif not isinstance(reference, str) or not reference:
            invalid.append("reference_audio")
        else:
            path = Path(reference)
            allowed_root = self.repository.task_dir(task_id) / "inputs"
            candidate = (self.repository.task_dir(task_id) / path).resolve()
            if path.is_absolute() or ".." in path.parts or candidate.parent != allowed_root.resolve() or not candidate.is_file() or candidate.stat().st_size <= 0:
                invalid.append("reference_audio")
        if invalid:
            raise DomainError("VALIDATION_ERROR", "必要输入无效", details={"invalid_fields": sorted(set(invalid))})

    def cancel_run(self, task_id: str, run_id: str, context: CommandContext | None = None) -> dict[str, Any]:
        """取消运行。"""
        run = self.repository.get_run(task_id, run_id)
        run.status = RunStatus.CANCELLED
        self.repository.save_run(run)
        self.telemetry.append_event(task_id, run_id, {"event_type": "RunCancelled"})
        return {"ok": True, "status": "cancelled"}

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

    def segment_script(
        self,
        task_id: str,
        run_id: str,
        script: str,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Legacy compatibility: segment script text, persist preparation, then run generate-visual-anchors.

        This is the public entrypoint used by the ``/stages/segment-script``
        HTTP alias.  It writes ``script_preparation`` into ``task.json`` and
        delegates to :meth:`generate_visual_anchors`.
        """
        if not script.strip():
            raise ValueError("脚本不能为空")

        task = self.repository.get_task(task_id)
        context = context or CommandContext(entrypoint=Entrypoint.CLI)

        # Segment / prepare
        preparation = prepare_script(script, target_chars=80, min_chars=35, max_chars=140)

        # Persist into task.json so generate_visual_anchors can read it
        task_json_path = self.repository.task_dir(task_id) / "task.json"
        task_data = json.loads(task_json_path.read_text(encoding="utf-8"))
        task_data["script_preparation"] = preparation
        task_data.setdefault("visual_anchor_enabled", True)
        self.repository.write_json(task_json_path, task_data)

        return self.generate_visual_anchors(task_id, run_id, context)

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

    def import_partial_historical_final(self, **kwargs: Any) -> dict[str, Any]:
        return self.repository.import_partial_historical_final(**kwargs)

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
            if self.service_resolver is None:
                raise DomainError("CAPABILITY_NOT_AVAILABLE", "ServiceResolver 未注入，无法构造 TextModel")
            text_def = self.service_resolver.resolve("text_generation")
            text_model = self.provider_factory.create_adapter(text_def)
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
        # VoiceUnitService persists reconciled alignment warnings.  Reload so
        # the command response cannot echo stale warnings from before a retry.
        run = self.repository.get_run(task_id, run_id)

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
        with self.repository.task_lock(task_id):
            self._require_native_task(self.repository.get_task(task_id))
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

            execution_plan = self._execution_plan(task_id)
            return self.pipeline.run_pipeline(
                task_id, run_id,
                policy="targeted",
                target_stage=stage,
                context=context,
                execution_plan=execution_plan,
                manual_trigger_stage=stage if stage in execution_plan.manual_stages else None,
            )

    def stage_run(
        self,
        task_id: str,
        run_id: str,
        stage: str,
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Explicitly trigger a stage, including a configured manual gate."""
        self._require_native_task(self.repository.get_task(task_id))
        if stage not in CANONICAL_STAGES: raise DomainError("VALIDATION_ERROR", "未知 Stage")
        gates = self.repository.get_gates(task_id, run_id)
        blocked = [gate.stage_id for gate in gates[:CANONICAL_STAGES.index(stage)] if gate.status != GATE_APPROVED]
        if blocked: raise DomainError("STAGE_GATE_REQUIRED", "上游 Stage Gate 尚未批准", details={"unapproved_stages": blocked})
        # Formal phase-one path deliberately does not ask PipelineOrchestrator
        # to repair dependencies: one explicit HTTP/Skill action owns one Stage.
        from csboard.application.work_orders import STAGE_INPUTS
        store = FilesystemArtifactStore(self.repository)
        missing = [key for key in STAGE_INPUTS[stage] if not self._valid_artifact(task_id, run_id, key)]
        if missing: raise DomainError("STAGE_GATE_REQUIRED", "上游 Artifact 尚未验证", details={"missing_artifacts": missing})
        context = context or CommandContext(entrypoint=Entrypoint.CLI)
        result = self.pipeline._execute_stage(task_id, run_id, stage, context)
        return self._stage_response(task_id, run_id, stage, result)

    def _stage_response(self, task_id: str, run_id: str, stage: str, result: dict[str, Any]) -> dict[str, Any]:
        run = self.repository.get_run(task_id, run_id)
        for key, expected in {"task_id": task_id, "run_id": run_id, "trace_id": run.trace_id, "stage": stage}.items():
            if key in result and result[key] != expected:
                safe = {"ok": False, "task_id": task_id, "run_id": run_id, "trace_id": run.trace_id, "stage": stage, "error": "STAGE_RESPONSE_IDENTITY_CONFLICT"}
                return {"ok": False, "task_id": task_id, "run_id": run_id, "trace_id": run.trace_id, "stage": stage, "stages_executed": [stage], "results": [safe], "next_stage": None, "next_action": {"code": "FIX_STAGE_RESULT"}}
        state = result.get("result")
        successful = bool(result.get("ok")) and state in {"succeeded", "skipped"}
        if successful and not self._exit_artifacts_valid(task_id, run_id, stage):
            return {"ok": False, "task_id": task_id, "run_id": run_id, "trace_id": run.trace_id, "stage": stage, "stages_executed": [stage], "results": [result], "next_stage": None, "next_action": {"code": "STAGE_OUTPUT_INVALID"}}
        if successful:
            try:
                self.mark_gate_waiting(task_id, run_id, stage)
            except Exception:
                return {"ok": False, "task_id": task_id, "run_id": run_id, "trace_id": run.trace_id, "stage": stage, "stages_executed": [stage], "results": [result], "next_stage": None, "next_action": {"code": "STAGE_GATE_PERSIST_FAILED"}}
            gate = self.get_gate(task_id, run_id, stage)
            if gate["status"] != GATE_WAITING:
                return {"ok": False, "task_id": task_id, "run_id": run_id, "trace_id": run.trace_id, "stage": stage, "stages_executed": [stage], "results": [result], "next_stage": None, "next_action": {"code": "STAGE_GATE_PERSIST_FAILED"}}
            next_stage = CANONICAL_STAGES[CANONICAL_STAGES.index(stage) + 1] if stage != CANONICAL_STAGES[-1] else None
            return {"ok": True, "task_id": task_id, "run_id": run_id, "trace_id": run.trace_id, "stage": stage, "stages_executed": [stage], "results": [result], "next_stage": next_stage, "next_action": {"code": "GATE_REVIEW_REQUIRED"}}
        return {"ok": False, "task_id": task_id, "run_id": run_id, "trace_id": run.trace_id, "stage": stage, "stages_executed": [stage], "results": [result], "next_stage": None, "next_action": {"code": "FIX_STAGE_RESULT"}}

    def _valid_artifact(self, task_id: str, run_id: str, key: str) -> bool:
        import hashlib
        item = FilesystemArtifactStore(self.repository).get(task_id, run_id, key)
        if not item or item.get("status", "succeeded") != "succeeded": return False
        path = self.repository.run_dir(task_id, run_id) / "artifacts" / str(item.get("relative_path", ""))
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == item.get("sha256")

    def _exit_artifacts_valid(self, task_id: str, run_id: str, stage: str) -> bool:
        from csboard.application.work_orders import STAGE_OUTPUTS
        return all(self._valid_artifact(task_id, run_id, key) for key in STAGE_OUTPUTS[stage])

    def list_gates(self, task_id: str, run_id: str) -> dict[str, Any]: return {"items": [gate.to_dict() for gate in self.repository.get_gates(task_id, run_id)]}
    def get_gate(self, task_id: str, run_id: str, stage: str) -> dict[str, Any]:
        if stage not in CANONICAL_STAGES: raise DomainError("VALIDATION_ERROR", "未知 Stage")
        return next(gate.to_dict() for gate in self.repository.get_gates(task_id, run_id) if gate.stage_id == stage)
    def mark_gate_waiting(self, task_id: str, run_id: str, stage: str) -> None:
        run, gates = self.repository.get_run(task_id, run_id), self.repository.get_gates(task_id, run_id)
        changed = [StageGate(**{**gate.to_dict(), "status": GATE_WAITING, "attempt": run.stages[stage].attempt if stage in run.stages else gate.attempt, "revision": gate.revision + 1}) if gate.stage_id == stage else gate for gate in gates]
        self.repository.save_gates(task_id, run_id, changed)
    def decide_gate(self, task_id: str, run_id: str, stage: str, decision: str, actor: str, expected_revision: int | None = None, note: str | None = None, evidence: list[dict[str, str]] | None = None) -> dict[str, Any]:
        if stage not in CANONICAL_STAGES or decision not in {"approve", "reject", "redo"} or not actor.strip(): raise DomainError("VALIDATION_ERROR", "Gate 决定、Stage 和 actor 无效")
        gates = self.repository.get_gates(task_id, run_id); gate = next(item for item in gates if item.stage_id == stage)
        if expected_revision is not None and (isinstance(expected_revision, bool) or expected_revision != gate.revision): raise DomainError("GATE_DECISION_CONFLICT", "Gate revision 已变化")
        wanted = {"approve": GATE_APPROVED, "reject": GATE_REJECTED, "redo": GATE_REDO}[decision]
        if not isinstance(evidence or [], list) or len(evidence or []) > 100: raise DomainError("VALIDATION_ERROR", "evidence 无效")
        allowed = {"logical_key", "sha256", "visual_id", "candidate_id", "revision", "source"}
        if any(not isinstance(item, dict) or set(item) - allowed or not isinstance(item.get("logical_key"), str) or not isinstance(item.get("sha256"), str) for item in (evidence or [])): raise DomainError("VALIDATION_ERROR", "evidence 无效")
        clean = [{key: str(value) for key, value in item.items()} for item in (evidence or [])]
        if decision == "approve" and (not clean or not self._exit_artifacts_valid(task_id, run_id, stage)):
            raise DomainError("VALIDATION_ERROR", "出口 Artifact 或 evidence 未验证")
        if decision == "approve" and any(not self._valid_artifact(task_id, run_id, item["logical_key"]) or FilesystemArtifactStore(self.repository).get(task_id, run_id, item["logical_key"]).get("sha256") != item["sha256"] for item in clean): raise DomainError("VALIDATION_ERROR", "evidence 与当前 Artifact 不一致")
        if gate.status == wanted and gate.actor == actor and list(gate.evidence) == clean: return gate.to_dict()
        if gate.status == GATE_APPROVED: raise DomainError("GATE_DECISION_CONFLICT", "已批准的 Gate 不能被静默覆盖")
        if gate.status != GATE_WAITING: raise DomainError("INVALID_STATE", "当前 Gate 尚不可决定")
        replacement = StageGate(**{**gate.to_dict(), "status": wanted, "decision": decision, "actor": actor.strip(), "decided_at": utc_now(), "revision": gate.revision + 1, "evidence": tuple(clean)})
        try: self.repository.replace_gate(task_id, run_id, stage, gate.revision, replacement)
        except RuntimeError: raise DomainError("GATE_DECISION_CONFLICT", "Gate revision 已变化")
        payload = {"stage": stage, "decision": decision, "actor": actor.strip(), "attempt": replacement.attempt, "revision": replacement.revision, "evidence": clean}
        self.telemetry.append_event(task_id, run_id, {"event_type": "StageGateDecided", **payload}); self.telemetry.append_audit(task_id, run_id, {"action": "stage.gate", **payload})
        return replacement.to_dict()

    def pipeline_run(
        self,
        task_id: str,
        run_id: str | None = None,
        policy: str = "auto",
        target_stage: str | None = None,
        context: CommandContext | None = None,
        manual_trigger_stage: str | None = None,
    ) -> dict[str, Any]:
        """Run the pipeline with the given policy."""
        task = self.repository.get_task(task_id)
        self._require_native_task(task)
        if run_id is None:
            run_id = task.active_run_id
        if not run_id:
            raise NotFoundError("任务没有活跃的运行")
        with self.repository.task_lock(task_id):
            context = context or CommandContext(entrypoint=Entrypoint.CLI)
            result = self.pipeline.run_pipeline(
                task_id, run_id, policy, target_stage, context,
                execution_plan=self._execution_plan(task_id),
                manual_trigger_stage=manual_trigger_stage,
            )
            if result.get("state") != "waiting-manual-trigger" or result.get("stages_executed"):
                self.telemetry.append_audit(task_id, run_id, {
                    "action": "pipeline.run",
                    "policy": policy,
                    "command_id": context.command_id,
                })
            return result

    def pipeline_resume(
        self,
        task_id: str,
        run_id: str | None = None,
        policy: str = "auto",
        context: CommandContext | None = None,
    ) -> dict[str, Any]:
        """Resume a pipeline from the last successful stage."""
        task = self.repository.get_task(task_id)
        self._require_native_task(task)
        if run_id is None:
            run_id = task.active_run_id
        if not run_id:
            raise NotFoundError("任务没有活跃的运行")
        with self.repository.task_lock(task_id):
            context = context or CommandContext(entrypoint=Entrypoint.CLI)
            result = self.pipeline.resume_pipeline(
                task_id, run_id, policy, context,
                execution_plan=self._execution_plan(task_id),
            )
            if result.get("state") != "waiting-manual-trigger" or result.get("stages_executed"):
                self.telemetry.append_audit(task_id, run_id, {
                    "action": "pipeline.resume",
                    "policy": policy,
                    "command_id": context.command_id,
                })
            return result

    def _execution_plan(self, task_id: str) -> ExecutionPlan:
        """Load the sole persisted execution decision source for every entrypoint."""
        request = self.repository.get_request(task_id) or {}
        return ExecutionPlan.from_dict(request.get("execution_plan", {}))

    @staticmethod
    def _require_native_task(task: Task) -> None:
        """P5: legacy projections are observable, never executable here."""
        if task.pipeline_id != "mountain-av-v1":
            raise DomainError("LEGACY_READ_ONLY", "历史任务仅支持只读查看，不能执行、重试或恢复")

    def work_order_show(self, task_id: str, run_id: str, stage: str) -> dict[str, Any]:
        """Return the deterministic persisted Stage Work Order view."""
        return WorkOrderService(self.repository).show(task_id, run_id, stage)

    def work_order_import(self, task_id: str, run_id: str, work_order_id: str, manifest_path: str) -> dict[str, Any]:
        return IllustrationCandidateService(self.repository).import_manifest(
            task_id, run_id, work_order_id, manifest_path
        )

    def work_order_validate(self, task_id: str, run_id: str, work_order_id: str) -> dict[str, Any]:
        return IllustrationCandidateService(self.repository).validate(task_id, run_id, work_order_id)

    def work_order_accept(self, task_id: str, run_id: str, work_order_id: str) -> dict[str, Any]:
        result = IllustrationCandidateService(self.repository).accept(task_id, run_id, work_order_id)
        return self._stage_response(task_id, run_id, "generate-illustrations", result)

    def work_order_reject(self, task_id: str, run_id: str, work_order_id: str, reason: str) -> dict[str, Any]:
        return IllustrationCandidateService(self.repository).reject(task_id, run_id, work_order_id, reason)

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
        voice_snapshot = request.get("voice_snapshot") if isinstance(request.get("voice_snapshot"), dict) else {}
        voice_id = str(voice_snapshot.get("voice_id") or request.get("voice_asset_id") or "")
        voice_config = {
            key: voice_snapshot[key]
            for key in ("language", "emotion_mode", "emotion_weight", "engine", "compatibility")
            if key in voice_snapshot
        }
        if request.get("voice_source") == "voice-asset":
            if not voice_id:
                raise DomainError("VALIDATION_ERROR", "任务请求中缺少 voice asset snapshot")
            try:
                audio = self.asset_repository.get_voice_content(voice_id)
                voice_asset = self.asset_repository.get_voice_asset(voice_id)
            except (NotFoundError, DomainError) as exc:
                raise DomainError("VALIDATION_ERROR", "音色资产内容不可用") from exc
            # The provider receives only an internal execution file; the stable
            # asset id and sanitized snapshot are the request's public contract.
            reference_audio = f"inputs/.voice-assets/{voice_id}.{voice_asset.format}"
            internal_path = self.repository.task_dir(task_id) / reference_audio
            internal_path.parent.mkdir(parents=True, exist_ok=True)
            if not internal_path.exists() or internal_path.read_bytes() != audio:
                internal_path.write_bytes(audio)
        if not reference_audio:
            raise DomainError("VALIDATION_ERROR", "任务请求中缺少 reference_audio 字段")

        # 解析相对路径：inputs/reference.wav → task_dir/inputs/reference.wav
        ref_path = Path(reference_audio)
        if not ref_path.is_absolute():
            ref_path = self.repository.task_dir(task_id) / ref_path
        if not ref_path.exists():
            raise DomainError("VALIDATION_ERROR", f"参考音频文件不存在: {reference_audio}")

        # 动态解析：speech_synthesis + speech_alignment（必须通过 ServiceResolver）
        if self.service_resolver is None:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", "ServiceResolver 未注入，无法构造 TTS/alignment/media adapter")
        tts_def = self.service_resolver.resolve("speech_synthesis")
        tts = self.provider_factory.create_adapter(tts_def)
        alignment_def = self.service_resolver.resolve("speech_alignment")
        alignment = self.provider_factory.create_adapter(alignment_def)
        media_def = self.service_resolver.resolve("media")
        media = self.provider_factory.create_adapter(media_def)

        return self.clone_voice(
            task_id, run_id, tts, alignment, media,
            reference_audio=ref_path,
            voice_id=voice_id,
            voice_config=voice_config,
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
        text_model: TextModelPort | None,
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

        if task.engine is Engine.INFOGRAPHIC_REMOTION:
            result = self._plan_storyboard_infographic(task_id, run_id, task, context)
        else:
            request = self._read_request(task_id)
            snapshot = request.get("style_snapshot") if isinstance(request.get("style_snapshot"), dict) else {}
            service = StoryboardService(text_model, self.repository, {
                "style": snapshot.get("prompt_text") or request.get("style") or "简约白板手绘风",
                "color_scheme": snapshot.get("color_scheme") or "黑白为主，点缀彩色",
            })
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

    def _plan_storyboard_infographic(
        self,
        task_id: str,
        run_id: str,
        task: Any,
        context: CommandContext,
    ) -> dict[str, Any]:
        """Storyboard path for infographic-remotion engine.

        Reads av-plan and timeline, converts to InfographicStoryboard via
        voice_units_to_pages(), then to Remotion props via
        InfographicStoryboardAdapter.  Embeds both the standard visuals
        array and the remotion_props in the storyboard artifact so the
        render stage can use them directly.
        """
        from csboard.adapters.remotion.storyboard_adapter import InfographicStoryboardAdapter
        from csboard.application.av_artifacts import storyboard_document
        from csboard.domain.infographic import voice_units_to_pages

        store = FilesystemArtifactStore(self.repository)

        av_plan = self._read_artifact(store, task_id, run_id, "planning.av-plan")
        timeline = self._read_artifact(store, task_id, run_id, "timing.timeline")
        if not av_plan:
            raise DomainError("VALIDATION_ERROR", "请先运行 generate-visual-anchors 生成 av-plan")
        if not timeline:
            raise DomainError("VALIDATION_ERROR", "请先运行 clone-voice 生成 timeline")

        voice_units = av_plan.get("voice_units", [])
        timeline_units = timeline.get("units", [])

        # Build visuals list for storyboard document (whiteboard-compatible)
        visuals: list[dict[str, Any]] = []
        timing_by_unit: dict[str, dict] = {u["unit_id"]: u for u in timeline_units}
        for unit in voice_units:
            unit_timing = timing_by_unit.get(unit["unit_id"], {})
            for vt in unit_timing.get("visual_timings", []):
                visuals.append({
                    "visual_id": vt["visual_id"],
                    "unit_id": unit["unit_id"],
                    "text": unit.get("text", ""),
                    "order": 1,
                    "start_ms": vt.get("start_ms", 0),
                    "end_ms": vt.get("end_ms", 0),
                    "prompt": unit.get("text", ""),
                })

        # Convert to InfographicStoryboard → Remotion props
        infographic_sb = voice_units_to_pages(voice_units, timeline_units, visuals)
        adapter = InfographicStoryboardAdapter()
        remotion_props = adapter.to_remotion_props(infographic_sb)

        # Build storyboard document with embedded remotion_props
        bible = {"style": "动态信息图", "color_scheme": "多彩", "composition_rules": [], "mood": "专业", "visual_metaphors": []}
        doc = storyboard_document(task_id, run_id, visuals, bible, task.engine)
        doc["remotion_props"] = remotion_props
        doc["voice_units"] = voice_units  # embed for renderer

        artifact = store.commit_bytes(
            task_id, run_id, "planning.storyboard", "planning/storyboard.json",
            json_bytes(doc), "plan-storyboard",
        )

        return {
            "storyboard": doc,
            "visual_count": len(visuals),
            "bible": bible,
            "artifact_key": artifact.artifact_key,
        }

    def _read_artifact(self, store: FilesystemArtifactStore, task_id: str, run_id: str, key: str) -> dict[str, Any] | None:
        """Read an artifact by key, returning parsed JSON or None."""
        ref = store.get(task_id, run_id, key)
        if not ref:
            return None
        path = self.repository.run_dir(task_id, run_id) / "artifacts" / ref["relative_path"]
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

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
        text_model = None
        if self.provider_factory is not None:
            try:
                if self.service_resolver is not None:
                    text_def = self.service_resolver.resolve("text_generation")
                    text_model = self.provider_factory.create_adapter(text_def)
                else:
                    text_model = self.provider_factory.create_text_model()
            except (DomainError, ValueError):
                # Storyboard prompt construction has a deterministic local
                # path; absence of an optional enhancement service is not a
                # reason to block the production workflow.
                text_model = None
        return self.plan_storyboard(task_id, run_id, text_model, context)

    def _exec_generate_illustrations(self, task_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for generate-illustrations. Uses ServiceResolver + ProviderFactory.create_adapter."""
        if self.provider_factory is None:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", "ProviderFactory 未注入，无法构造 image model")
        if self.service_resolver is None:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", "ServiceResolver 未注入，无法构造 image model")
        image_def = self.service_resolver.resolve("image_generation")
        image_model = self.provider_factory.create_adapter(image_def)
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
            if not ref or ref.get("status", "succeeded") != "succeeded":
                return None
            candidate = run_dir / "artifacts" / str(ref.get("relative_path", ""))
            try:
                candidate.resolve().relative_to((run_dir / "artifacts").resolve())
            except ValueError:
                return None
            if not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest() != ref.get("sha256"):
                return None
            return candidate
        timeline_path = artifact_path("timing.timeline")
        storyboard_path = artifact_path("planning.storyboard")
        illustration_manifest_path = artifact_path("illustrations.manifest")

        if timeline_path is None or not timeline_path.exists():
            raise DomainError("VALIDATION_ERROR", "timeline 不存在，请先运行 clone-voice")
        if storyboard_path is None or not storyboard_path.exists():
            raise DomainError("VALIDATION_ERROR", "storyboard 不存在，请先运行 plan-storyboard")
        if illustration_manifest_path is None or not illustration_manifest_path.exists():
            raise DomainError("VALIDATION_ERROR", "illustration-manifest 不存在，请先运行 generate-illustrations")
        if task.engine is Engine.INFOGRAPHIC_REMOTION:
            for label, path in (("timeline", timeline_path), ("storyboard", storyboard_path),
                                ("illustration-manifest", illustration_manifest_path)):
                try:
                    document = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise DomainError("ARTIFACT_INDEX_INVALID", f"{label} 输入不可读取") from exc
                if document.get("task_id") != task_id or document.get("run_id") != run_id:
                    raise DomainError("ARTIFACT_RUN_MISMATCH", f"{label} 不属于当前 run")

        # Indexable renderer output must remain inside this run's artifacts.
        output_dir = run_dir / "artifacts" / "render"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build render request
        request = RenderRequest(
            timeline_path=timeline_path,
            storyboard_path=storyboard_path,
            illustration_manifest_path=illustration_manifest_path,
            output_dir=output_dir,
            request_id=f"{task_id}:{run_id}:render",
        )

        try:
            result = renderer.render(request)
            output_path = Path(result.output_path).resolve()
            output_path.relative_to(output_dir.resolve())
            if not output_path.is_file() or output_path.stat().st_size <= 0:
                raise DomainError("RENDER_OUTPUT_INVALID", "renderer 未生成可索引输出")
        except Exception:
            run = self.repository.get_run(task_id, run_id)
            run.status = RunStatus.FAILED
            run.stages["render-visuals"] = StageState(StageStatus.FAILED, run.stages["render-visuals"].attempt)
            self.repository.save_run(run)
            raise

        # Build render manifest
        output_bytes = output_path.read_bytes()
        output_ref = store.commit_bytes(task_id, run_id, "render.video", "render/infographic.mp4", output_bytes, "render-visuals")
        probe = result.provider_metadata.get("probe", {})
        render_manifest = {
            **render_manifest_document(task_id, run_id, result.provider_metadata.get("clips", []), task.engine),
            "output_relative_path": f"artifacts/{output_ref.relative_path}",
            "output_sha256": output_ref.sha256,
            "size_bytes": output_ref.size_bytes,
            "duration_ms": result.duration_ms,
            "frames": result.frames,
            "probe_sha256": hashlib.sha256(json.dumps(probe, sort_keys=True).encode()).hexdigest(),
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
            "artifacts": ["render.video", artifact_key],
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
        """Stage executor for render-visuals. Routes by task.engine."""
        task = self.repository.get_task(task_id)

        if task.engine is Engine.INFOGRAPHIC_REMOTION:
            from csboard.adapters.remotion.renderer_adapter import RemotionRendererAdapter
            renderer = (self.infographic_renderer_factory()
                        if self.infographic_renderer_factory is not None
                        else RemotionRendererAdapter(self.root / "video_renderer" / "render.mjs"))
        else:
            # WHITEBOARD path — unchanged ServiceResolver routing
            if self.provider_factory is None:
                raise DomainError("CAPABILITY_NOT_AVAILABLE", "ProviderFactory 未注入，无法构造 renderer")
            if self.service_resolver is None:
                raise DomainError("CAPABILITY_NOT_AVAILABLE", "ServiceResolver 未注入，无法构造 renderer adapter")
            render_def = self.service_resolver.resolve("rendering")
            renderer = self.provider_factory.create_adapter(render_def)

        return self.render_visuals(task_id, run_id, renderer, context)

    def _exec_compose_video(self, task_id: str, run_id: str, context: CommandContext) -> dict[str, Any]:
        """Stage executor for compose-video. Uses ServiceResolver + ProviderFactory.create_adapter."""
        if self.provider_factory is None:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", "ProviderFactory 未注入，无法构造 media adapter")
        if self.service_resolver is None:
            raise DomainError("CAPABILITY_NOT_AVAILABLE", "ServiceResolver 未注入，无法构造 media adapter")
        media_def = self.service_resolver.resolve("media")
        media = self.provider_factory.create_adapter(media_def)
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
