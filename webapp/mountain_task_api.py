"""Mountain Task API — /api/v1/tasks 路由。

从 mountain_v1_api.py 拆分，只包含 Task/Run/Stage/Artifact/Log API。
不包含固定 Provider API（已由 mountain_service_api.py 替代）。
不依赖 PROVIDER_PROFILES。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, File, Form, UploadFile
from fastapi.responses import FileResponse

from csboard.adapters.filesystem import FilesystemTaskRepository
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.commands import MountainCommands
from csboard.application.context import CommandContext
from csboard.application.pipeline import STAGE_ORDER
from csboard.domain.enums import Engine, Entrypoint, RunStatus, StageStatus
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.script_preparation import prepare_script
from webapp.error_contract import domain_error_response


def mountain_task_router(
    data_dir: Path,
    commands: MountainCommands | None = None,
    repository: FilesystemTaskRepository | None = None,
    telemetry: JsonlTelemetry | None = None,
    service_resolver=None,
    provider_factory=None,
) -> APIRouter:
    """创建 /api/v1 路由器 — Task/Run/Stage 相关端点。

    所有依赖由 create_app() 注入。commands 是唯一 MountainCommands 实例。
    """
    repository = repository or FilesystemTaskRepository(data_dir)
    telemetry = telemetry or JsonlTelemetry(repository)
    # 若未注入 commands，则回退创建（CLI/测试兼容）
    if commands is None:
        commands = MountainCommands(
            data_dir,
            provider_factory=provider_factory,
            service_resolver=service_resolver,
            repository=repository,
            telemetry=telemetry,
        )
    router = APIRouter(prefix="/api/v1", tags=["mountain-tasks"])

    def _context() -> CommandContext:
        """创建 Web 入口的 CommandContext。"""
        return CommandContext(entrypoint=Entrypoint.WEB)

    # ── Task ──────────────────────────────────────────────────────

    @router.post("/tasks")
    def create_task(payload: dict = Body(...)):
        """创建新任务。"""
        try:
            title = str(payload.get("title", ""))
            engine = Engine(payload.get("engine", "whiteboard"))
            pipeline_id = payload.get("pipeline_id", "mountain-av-v1")
            return commands.create_task(
                title, pipeline_id, engine, context=_context()
            )
        except ValueError as error:
            return domain_error_response(DomainError("VALIDATION_ERROR", str(error)), status_code=400)

    @router.get("/tasks")
    def list_tasks(
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        q: str | None = None,
    ):
        """列出任务 — 委托 Application 层执行 filter→sort→cursor→limit。"""
        return commands.list_tasks(limit=limit, cursor=cursor, status=status, q=q)

    @router.get("/tasks/{task_id}")
    def get_task(task_id: str):
        """获取任务详情。"""
        try:
            task = repository.get_task(task_id)
            run = (
                repository.get_run(task_id, task.active_run_id)
                if task.active_run_id
                else None
            )
            return _task_detail_view(task, run)
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    # ── Input Upload ──────────────────────────────────────────────────

    # 上传大小上限：50MB
    MAX_UPLOAD_BYTES = 50 * 1024 * 1024
    # 分块大小：1MB
    CHUNK_SIZE = 1024 * 1024

    @router.post("/tasks/{task_id}/inputs")
    async def upload_inputs(
        task_id: str,
        script: str = Form(...),
        reference: UploadFile | None = File(None),
        style: str = Form("极简粗线简笔白板风"),
        include_subtitles: bool = Form(True),
        pen_text: str = Form(""),
        stroke_detail: str = Form("detailed"),
        target_chars: int = Form(80),
        min_chars: int = Form(35),
        max_chars: int = Form(140),
        visual_anchor_enabled: bool = Form(True),
    ):
        """上传任务输入（文案和参考音频）— 委托 Application 层。"""
        txn_dir = None
        staging_ref = None
        reference_audio_filename = None

        try:
            # 分块写入 staging 文件（在任务目录内，同一文件系统）
            if reference is not None:
                reference_audio_filename = reference.filename
                suffix = Path(reference_audio_filename or "reference.wav").suffix.lower() or ".wav"
                if suffix not in {".wav", ".mp3", ".m4a", ".ogg", ".flac"}:
                    return domain_error_response(
                        DomainError("VALIDATION_ERROR", "参考音频格式不支持"),
                        status_code=400,
                    )

                # 在任务目录内创建 staging（同一文件系统）
                txn_dir = repository.create_staging(task_id)
                staging_ref = txn_dir / f"reference{suffix}"

                # 分块写入，检查大小上限
                total_bytes = 0
                with staging_ref.open("wb") as f:
                    while chunk := await reference.read(CHUNK_SIZE):
                        total_bytes += len(chunk)
                        if total_bytes > MAX_UPLOAD_BYTES:
                            return domain_error_response(
                                DomainError("VALIDATION_ERROR", f"参考音频超过大小上限 ({MAX_UPLOAD_BYTES // (1024*1024)}MB)"),
                                status_code=400,
                            )
                        f.write(chunk)

            # 委托 Application 处理
            result = commands.save_inputs(
                task_id,
                script=script,
                txn_dir=txn_dir,
                reference_audio_filename=reference_audio_filename,
                style=style,
                include_subtitles=include_subtitles,
                pen_text=pen_text,
                stroke_detail=stroke_detail,
                target_chars=target_chars,
                min_chars=min_chars,
                max_chars=max_chars,
                visual_anchor_enabled=visual_anchor_enabled,
                context=_context(),
            )

            return result
        except DomainError as error:
            return domain_error_response(error, status_code=400)
        except Exception as error:
            # 内部错误不暴露绝对路径或异常原文
            return domain_error_response(
                DomainError("INTERNAL_ERROR", "输入保存失败"),
                status_code=500,
            )
        finally:
            # 确保 staging 目录被清理（Repository 也会清理）
            if txn_dir and txn_dir.exists():
                import shutil
                shutil.rmtree(txn_dir, ignore_errors=True)

    @router.get("/tasks/{task_id}/inputs")
    def get_inputs(task_id: str):
        """读取已保存的任务输入 — 委托 Application 层。"""
        try:
            return commands.get_inputs(task_id)
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    # ── Run Operations ──────────────────────────────────────────────────

    @router.post("/tasks/{task_id}/runs/{run_id}/start")
    def start_run(task_id: str, run_id: str, policy: str = "auto"):
        """启动标准流程 — 委托 Application 层。"""
        try:
            return commands.start_run(task_id, run_id, policy, context=_context())
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)
        except DomainError as error:
            return domain_error_response(error, status_code=400)

    @router.post("/tasks/{task_id}/runs/{run_id}/cancel")
    def cancel_run(task_id: str, run_id: str):
        """取消运行 — 委托 Application 层。"""
        try:
            return commands.cancel_run(task_id, run_id, _context())
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    @router.post("/tasks/{task_id}/runs/{run_id}/retry")
    def retry_run(task_id: str, run_id: str):
        """重试失败的运行。"""
        try:
            return commands.pipeline_resume(
                task_id, run_id, context=_context()
            )
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)
        except DomainError as error:
            return domain_error_response(error, status_code=400)

    # ── Stage Operations ──────────────────────────────────────────────────

    @router.post("/tasks/{task_id}/runs/{run_id}/stages/{stage}/run")
    def run_stage(task_id: str, run_id: str, stage: str):
        """运行指定阶段。"""
        try:
            return commands.pipeline_run(
                task_id, run_id, "targeted", stage, _context()
            )
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)
        except DomainError as error:
            return domain_error_response(error, status_code=400)

    @router.post("/tasks/{task_id}/runs/{run_id}/stages/{stage}/retry")
    def retry_stage(
        task_id: str,
        run_id: str,
        stage: str,
        unit_id: str = None,
        visual_id: str = None,
    ):
        """重试指定阶段。"""
        try:
            return commands.stage_retry(
                task_id, run_id, stage, unit_id, visual_id, _context()
            )
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)
        except DomainError as error:
            return domain_error_response(error, status_code=400)

    # ── Pipeline Operations ──────────────────────────────────────────────────

    @router.post("/tasks/{task_id}/runs/{run_id}/pipeline/run")
    def pipeline_run(
        task_id: str,
        run_id: str,
        policy: str = "auto",
        target_stage: str = None,
    ):
        """运行 Pipeline。"""
        try:
            return commands.pipeline_run(
                task_id, run_id, policy, target_stage, _context()
            )
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)
        except DomainError as error:
            return domain_error_response(error, status_code=400)

    @router.post("/tasks/{task_id}/runs/{run_id}/pipeline/resume")
    def pipeline_resume(task_id: str, run_id: str, policy: str = "auto"):
        """恢复 Pipeline。"""
        try:
            return commands.pipeline_resume(
                task_id, run_id, policy, _context()
            )
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)
        except DomainError as error:
            return domain_error_response(error, status_code=400)

    # ── Run Status ──────────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/runs/{run_id}")
    def get_run(task_id: str, run_id: str):
        """获取 Run 详情。"""
        try:
            run = repository.get_run(task_id, run_id)
            return _run_view(run)
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    @router.get("/tasks/{task_id}/runs/{run_id}/stages")
    def get_stages(task_id: str, run_id: str):
        """获取所有阶段状态。"""
        try:
            run = repository.get_run(task_id, run_id)
            return {
                "items": [
                    {"stage": name, **state.to_dict()}
                    for name, state in run.stages.items()
                ]
            }
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    # ── Voice Units ──────────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/runs/{run_id}/units")
    def get_units(task_id: str, run_id: str):
        """获取 Voice Units。"""
        try:
            run_dir = repository.run_dir(task_id, run_id)
            plan_path = run_dir / "artifacts" / "planning" / "av-plan.json"
            if not plan_path.exists():
                return {"items": []}
            plan = repository.read_json(plan_path)
            timeline_path = run_dir / "artifacts" / "timing" / "timeline.json"
            timings = (
                {
                    item["unit_id"]: item
                    for item in repository.read_json(timeline_path).get("units", [])
                }
                if timeline_path.exists()
                else {}
            )
            return {
                "items": [
                    {**unit, "timing": timings.get(unit["unit_id"])}
                    for unit in plan.get("voice_units", [])
                ]
            }
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    # ── Artifacts ──────────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/runs/{run_id}/artifacts")
    def list_artifacts(task_id: str, run_id: str):
        """列出所有产物。"""
        try:
            run_dir = repository.run_dir(task_id, run_id)
            index_path = run_dir / "artifacts" / "index.json"
            if not index_path.exists():
                return {"items": []}
            index = repository.read_json(index_path)
            items = [
                {"artifact_key": key, **item}
                for key, item in index.get("artifacts", {}).items()
            ]
            return {"items": items}
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    @router.get("/tasks/{task_id}/runs/{run_id}/artifacts/{artifact_key}")
    def download_artifact(task_id: str, run_id: str, artifact_key: str):
        """下载产物文件。"""
        try:
            index = repository.read_json(
                repository.run_dir(task_id, run_id) / "artifacts" / "index.json"
            )
            item = index.get("artifacts", {}).get(artifact_key)
            if not item or item.get("status") != "succeeded":
                return domain_error_response(NotFoundError("产物不可用"), status_code=404)
            path = (
                repository.run_dir(task_id, run_id)
                / "artifacts"
                / str(item["relative_path"])
            )
            if not path.is_file():
                return domain_error_response(NotFoundError("产物文件不存在"), status_code=404)
            return FileResponse(path, filename=path.name)
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    @router.get("/tasks/{task_id}/runs/{run_id}/artifacts/{artifact_key}/content")
    def artifact_content(task_id: str, run_id: str, artifact_key: str):
        """获取产物内容（JSON 或文本）。"""
        try:
            index = repository.read_json(
                repository.run_dir(task_id, run_id) / "artifacts" / "index.json"
            )
            item = index.get("artifacts", {}).get(artifact_key)
            if not item:
                return domain_error_response(NotFoundError("产物不存在"), status_code=404)
            path = (
                repository.run_dir(task_id, run_id)
                / "artifacts"
                / str(item["relative_path"])
            )
            if not path.exists():
                return domain_error_response(NotFoundError("产物文件不存在"), status_code=404)
            if path.suffix == ".json":
                content = json.loads(path.read_text(encoding="utf-8"))
            else:
                content = path.read_text(encoding="utf-8")
            return {
                "artifact_key": artifact_key,
                "content": content,
                "metadata": item,
            }
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    # ── Events ──────────────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/runs/{run_id}/events")
    def get_events(task_id: str, run_id: str, after: int = 0):
        """获取事件列表（结构化脱敏）。"""
        try:
            from csboard.adapters.observability.redactor import DefaultRedactor
            redactor = DefaultRedactor()

            items = telemetry.read_events(task_id, run_id, after)
            # 使用 DefaultRedactor 结构化脱敏
            safe_items = [redactor.redact(entry) for entry in items]
            return {
                "items": safe_items,
                "next_cursor": items[-1]["sequence"] if items else after,
            }
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    # ── Logs ──────────────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/runs/{run_id}/logs")
    def get_logs(
        task_id: str,
        run_id: str,
        level: str = "",
        component: str = "",
        stage: str = "",
    ):
        """获取日志列表（结构化脱敏）。"""
        try:
            from csboard.adapters.observability.redactor import DefaultRedactor
            redactor = DefaultRedactor()

            path = (
                repository.run_dir(task_id, run_id)
                / "observability"
                / "logs.jsonl"
            )
            repository.get_run(task_id, run_id)
            raw_items = (
                []
                if not path.exists()
                else [
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line
                ]
            )
            # 过滤后脱敏
            filtered = [
                item
                for item in raw_items
                if (not level or item.get("level") == level)
                and (not component or item.get("component") == component)
                and (not stage or item.get("stage") == stage)
            ]
            # 使用 DefaultRedactor 结构化脱敏
            items = [redactor.redact(entry) for entry in filtered]
            return {"items": items}
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    # ── Trace ──────────────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/runs/{run_id}/trace")
    def get_trace(task_id: str, run_id: str):
        """获取 Trace 信息。"""
        try:
            run = repository.get_run(task_id, run_id)
            return {
                "trace_id": run.trace_id,
                "command_ids": run.command_ids,
                "entrypoint": run.entrypoint.value,
            }
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    # ── Metrics ──────────────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/runs/{run_id}/metrics")
    def get_metrics(task_id: str, run_id: str):
        """获取运行指标。"""
        try:
            run = repository.get_run(task_id, run_id)
            return {
                "run_status": run.status.value,
                "stage_attempts": {
                    name: state.attempt for name, state in run.stages.items()
                },
                "fallback_count": sum(
                    1
                    for warning in run.warnings
                    if "FALLBACK" in str(warning.get("code", ""))
                ),
            }
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    # ── Diagnostics ──────────────────────────────────────────────────────

    @router.post("/tasks/{task_id}/runs/{run_id}/diagnostics")
    def export_diagnostics(task_id: str, run_id: str):
        """导出诊断包。"""
        try:
            bundle = telemetry.export_diagnostic_bundle(task_id, run_id)
            return {
                "bundle_id": bundle.stem,
                "download_url": f"/api/v1/tasks/{task_id}/runs/{run_id}/diagnostics/{bundle.name}",
            }
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    @router.get("/tasks/{task_id}/runs/{run_id}/diagnostics/{filename}")
    def download_diagnostics(task_id: str, run_id: str, filename: str):
        """下载诊断包。"""
        if (
            not filename.startswith("diagnostic-")
            or not filename.endswith(".zip")
            or "/" in filename
        ):
            return domain_error_response(DomainError("VALIDATION_ERROR", "诊断包名称无效"), status_code=400)
        try:
            repository.get_run(task_id, run_id)
            path = (
                repository.run_dir(task_id, run_id) / "diagnostics" / filename
            )
            if not path.is_file():
                return domain_error_response(NotFoundError("诊断包不存在"), status_code=404)
            return FileResponse(
                path, media_type="application/zip", filename=filename
            )
        except NotFoundError as error:
            return domain_error_response(error, status_code=404)

    # ── Final Video ──────────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/runs/{run_id}/final")
    def download_final(task_id: str, run_id: str):
        """下载成片。"""
        path = (
            repository.run_dir(task_id, run_id)
            / "artifacts"
            / "output"
            / "final.mp4"
        )
        if not path.exists():
            return domain_error_response(NotFoundError("成片尚未生成"), status_code=404)
        return FileResponse(
            path, media_type="video/mp4", filename=f"cs-board-{task_id}.mp4"
        )

    # ── Helper Functions ──────────────────────────────────────────────────

    def _task_detail_view(task, run) -> dict[str, Any]:
        """构建 Task 详情视图。"""
        result = {
            "task": task.to_dict(),
            "active_run": run.to_dict() if run else None,
            "stages": [],
            "warnings": [],
            "artifacts": [],
            "trace": None,
        }
        if run:
            result["stages"] = [
                {"stage": name, **state.to_dict()}
                for name, state in run.stages.items()
            ]
            result["warnings"] = run.warnings
            result["trace"] = {
                "trace_id": run.trace_id,
                "command_ids": run.command_ids,
            }
            index_path = (
                repository.run_dir(task.task_id, run.run_id)
                / "artifacts"
                / "index.json"
            )
            if index_path.exists():
                index = repository.read_json(index_path)
                result["artifacts"] = [
                    {"artifact_key": key, **item}
                    for key, item in index.get("artifacts", {}).items()
                ]
        return result

    def _run_view(run) -> dict[str, Any]:
        """构建 Run 视图。"""
        return {
            "run_id": run.run_id,
            "task_id": run.task_id,
            "trace_id": run.trace_id,
            "status": run.status.value,
            "entrypoint": run.entrypoint.value,
            "target_stage": run.target_stage,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "stages": {
                name: state.to_dict() for name, state in run.stages.items()
            },
            "warnings": run.warnings,
        }

    return router
