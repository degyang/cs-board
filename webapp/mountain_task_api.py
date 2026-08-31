"""Mountain Task API — /api/v1/tasks 路由。

从 mountain_v1_api.py 拆分，只包含 Task/Run/Stage/Artifact/Log API。
不包含固定 Provider API（已由 mountain_service_api.py 替代）。
不依赖 PROVIDER_PROFILES。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
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


def mountain_task_router(data_dir: Path) -> APIRouter:
    """创建 /api/v1 路由器 — Task/Run/Stage 相关端点。"""
    repository = FilesystemTaskRepository(data_dir)
    telemetry = JsonlTelemetry(repository)
    router = APIRouter(prefix="/api/v1", tags=["mountain-tasks"])

    # service_registry / service_resolver / provider_factory 由外部注入
    # 通过 mountain_server.py 的 lifespan 或 app.state 传递
    _service_resolver = None
    _provider_factory = None

    def _get_commands() -> MountainCommands:
        """创建 MountainCommands 实例，注入 ProviderFactory。"""
        return MountainCommands(data_dir, provider_factory=_provider_factory)

    def _context() -> CommandContext:
        """创建 Web 入口的 CommandContext。"""
        return CommandContext(entrypoint=Entrypoint.WEB)

    def _set_dependencies(service_resolver, provider_factory):
        nonlocal _service_resolver, _provider_factory
        _service_resolver = service_resolver
        _provider_factory = provider_factory

    router.state_set_dependencies = _set_dependencies

    # ── Task ──────────────────────────────────────────────────────

    @router.post("/tasks")
    def create_task(payload: dict = Body(...)):
        """创建新任务。"""
        try:
            title = str(payload.get("title", ""))
            engine = Engine(payload.get("engine", "whiteboard"))
            pipeline_id = payload.get("pipeline_id", "mountain-av-v1")
            return _get_commands().create_task(
                title, pipeline_id, engine, context=_context()
            )
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @router.get("/tasks")
    def list_tasks(
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        q: str | None = None,
    ):
        """列出任务。"""
        items = []
        tasks_dir = data_dir / "tasks"
        if not tasks_dir.exists():
            return {"items": [], "next_cursor": None}

        all_paths = sorted(tasks_dir.glob("*/task.json"), reverse=True)

        if cursor:
            cursor_idx = -1
            for idx, p in enumerate(all_paths):
                if p.parent.name == cursor:
                    cursor_idx = idx + 1
                    break
            if cursor_idx > 0:
                all_paths = all_paths[cursor_idx:]

        _PRIORITY = {"running": 0, "failed": 1}

        def _sort_key(path: Path) -> tuple[int, str]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                status_val = data.get("status", "draft")
                priority = _PRIORITY.get(status_val, 2)
                updated = data.get("updated_at", "")
                return (priority, updated)
            except Exception:
                return (99, "")

        all_paths = sorted(all_paths, key=_sort_key, reverse=True)
        effective_limit = max(1, min(limit, 100))

        for path in all_paths:
            if len(items) >= effective_limit:
                break
            try:
                task = repository.get_task(path.parent.name)
                task_dict = task.to_dict()

                if status and task_dict.get("status") != status:
                    continue
                if q:
                    q_lower = q.lower()
                    title_match = q_lower in task_dict.get("title", "").lower()
                    id_match = q_lower in task_dict.get("task_id", "").lower()
                    if not title_match and not id_match:
                        continue

                active_run = None
                if task.active_run_id:
                    try:
                        run = repository.get_run(task.task_id, task.active_run_id)
                        current_stage = None
                        for stage_name in reversed(STAGE_ORDER):
                            stage_state = run.stages.get(stage_name)
                            if stage_state and stage_state.status in (StageStatus.RUNNING, StageStatus.FAILED):
                                current_stage = stage_name
                                break
                            if stage_state and stage_state.status == StageStatus.SUCCEEDED:
                                break
                        if current_stage is None and run.status == RunStatus.RUNNING:
                            for stage_name in STAGE_ORDER:
                                stage_state = run.stages.get(stage_name)
                                if not stage_state or stage_state.status == StageStatus.PENDING:
                                    current_stage = stage_name
                                    break

                        final_path = repository.run_dir(task.task_id, task.active_run_id) / "artifacts" / "final.mp4"
                        final_available = final_path.is_file()
                        error_code = getattr(run, 'error_code', None)

                        active_run = {
                            "run_id": run.run_id,
                            "status": run.status.value,
                            "current_stage": current_stage,
                            "started_at": run.started_at,
                            "retryable": run.status == RunStatus.FAILED,
                            "error_code": error_code,
                            "final_available": final_available,
                            "fallback_unit_count": None,
                        }
                    except NotFoundError:
                        pass

                task_dict.pop("script_preparation", None)
                task_dict.pop("visual_anchor_enabled", None)
                task_dict["active_run"] = active_run
                items.append(task_dict)
            except NotFoundError:
                continue

        next_cursor = items[-1]["task_id"] if len(items) >= effective_limit else None
        return {"items": items, "next_cursor": next_cursor}

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
            raise HTTPException(404, error.message) from error

    # ── Input Upload ──────────────────────────────────────────────────

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
        """上传任务输入（文案和参考音频）。"""
        try:
            repository.get_task(task_id)
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

        if len(script.strip()) < 10:
            raise HTTPException(400, "文案至少需要 10 个字")

        input_dir = repository.task_dir(task_id) / "inputs"

        if reference is not None:
            suffix = Path(reference.filename or "reference.wav").suffix.lower() or ".wav"
            if suffix not in {".wav", ".mp3", ".m4a", ".ogg", ".flac"}:
                raise HTTPException(400, "参考音频格式不支持")

            input_dir.mkdir(parents=True, exist_ok=True)
            target = input_dir / f"reference{suffix}"
            temporary = target.with_suffix(f"{suffix}.partial")
            with temporary.open("wb") as output:
                while chunk := await reference.read(1024 * 1024):
                    output.write(chunk)
            temporary.replace(target)
        else:
            has_audio = any(
                (input_dir / f"reference{ext}").is_file()
                for ext in (".wav", ".mp3", ".m4a", ".ogg", ".flac")
            )
            if not has_audio:
                raise HTTPException(400, "首次保存必须提供参考音频")

        request_data = {
            "script": script.strip(),
            "reference_audio": str(target) if reference else None,
            "style": style,
            "include_subtitles": include_subtitles,
            "pen_text": pen_text[:12],
            "stroke_detail": stroke_detail if stroke_detail in {"light", "standard", "detailed", "full"} else "detailed",
            "target_chars": target_chars,
            "min_chars": min_chars,
            "max_chars": max_chars,
            "visual_anchor_enabled": visual_anchor_enabled,
        }
        request_path = repository.task_dir(task_id) / "request.json"
        request_path.write_text(
            json.dumps(request_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        try:
            preparation = prepare_script(
                script.strip(),
                target_chars=target_chars,
                min_chars=min_chars,
                max_chars=max_chars,
            )
        except ValueError as exc:
            raise HTTPException(400, detail={"code": "VALIDATION_ERROR", "message": str(exc)}) from exc

        task_json_path = repository.task_dir(task_id) / "task.json"
        task_data = json.loads(task_json_path.read_text(encoding="utf-8"))
        task_data["script_preparation"] = preparation
        task_data["visual_anchor_enabled"] = visual_anchor_enabled
        task_json_path.write_text(
            json.dumps(task_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return {"ok": True, "task_id": task_id, "input_saved": True}

    @router.get("/tasks/{task_id}/inputs")
    def get_inputs(task_id: str):
        """读取已保存的任务输入。"""
        try:
            repository.get_task(task_id)
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

        request_path = repository.task_dir(task_id) / "request.json"
        if not request_path.exists():
            return {
                "task_id": task_id,
                "saved": False,
                "inputs": None,
                "reference_audio": {"uploaded": False, "filename": None, "content_type": None, "size_bytes": None},
            }

        request_data = json.loads(request_path.read_text(encoding="utf-8"))

        input_dir = repository.task_dir(task_id) / "inputs"
        audio_meta: dict[str, Any] = {"uploaded": False, "filename": None, "content_type": None, "size_bytes": None}
        for suffix in (".wav", ".mp3", ".m4a", ".ogg", ".flac"):
            candidate = input_dir / f"reference{suffix}"
            if candidate.is_file():
                audio_meta = {
                    "uploaded": True,
                    "filename": f"reference{suffix}",
                    "content_type": f"audio/{suffix.lstrip('.')}",
                    "size_bytes": candidate.stat().st_size,
                }
                break

        task_json_path = repository.task_dir(task_id) / "task.json"
        task_data = json.loads(task_json_path.read_text(encoding="utf-8"))
        preparation = task_data.get("script_preparation")
        visual_anchor_enabled = task_data.get("visual_anchor_enabled", True)

        return {
            "task_id": task_id,
            "saved": True,
            "inputs": {
                "script": request_data.get("script", ""),
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
            "visual_anchor_enabled": visual_anchor_enabled,
        }

    # ── Run Operations ──────────────────────────────────────────────────

    @router.post("/tasks/{task_id}/runs/{run_id}/start")
    def start_run(task_id: str, run_id: str, policy: str = "auto"):
        """启动标准流程。"""
        try:
            request_path = repository.task_dir(task_id) / "request.json"
            if not request_path.exists():
                raise HTTPException(400, "请先上传文案与参考音频")

            # 使用 ServiceResolver 检查 capability 可用性
            if _service_resolver is not None:
                from csboard.application.service_resolver import STAGE_CAPABILITY_MAP
                unavailable = []
                for stage_name, capability in STAGE_CAPABILITY_MAP.items():
                    try:
                        _service_resolver.resolve(capability)
                    except DomainError:
                        unavailable.append({"stage": stage_name, "capability": capability})
                if unavailable:
                    raise HTTPException(
                        400,
                        {
                            "code": "CAPABILITY_NOT_AVAILABLE",
                            "message": "缺少必要的服务配置",
                            "unavailable": unavailable,
                        },
                    )

            return _get_commands().pipeline_run(
                task_id, run_id, policy, context=_context()
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error

    @router.post("/tasks/{task_id}/runs/{run_id}/cancel")
    def cancel_run(task_id: str, run_id: str):
        """取消运行。"""
        try:
            run = repository.get_run(task_id, run_id)
            run.status = RunStatus.CANCELLED
            repository.save_run(run)
            telemetry.append_event(task_id, run_id, {"event_type": "RunCancelled"})
            return {"ok": True, "status": "cancelled"}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.post("/tasks/{task_id}/runs/{run_id}/retry")
    def retry_run(task_id: str, run_id: str):
        """重试失败的运行。"""
        try:
            return _get_commands().pipeline_resume(
                task_id, run_id, context=_context()
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error

    # ── Stage Operations ──────────────────────────────────────────────────

    @router.post("/tasks/{task_id}/runs/{run_id}/stages/{stage}/run")
    def run_stage(task_id: str, run_id: str, stage: str):
        """运行指定阶段。"""
        try:
            return _get_commands().pipeline_run(
                task_id, run_id, "targeted", stage, _context()
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error

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
            return _get_commands().stage_retry(
                task_id, run_id, stage, unit_id, visual_id, _context()
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error

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
            return _get_commands().pipeline_run(
                task_id, run_id, policy, target_stage, _context()
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error

    @router.post("/tasks/{task_id}/runs/{run_id}/pipeline/resume")
    def pipeline_resume(task_id: str, run_id: str, policy: str = "auto"):
        """恢复 Pipeline。"""
        try:
            return _get_commands().pipeline_resume(
                task_id, run_id, policy, _context()
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error

    # ── Run Status ──────────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/runs/{run_id}")
    def get_run(task_id: str, run_id: str):
        """获取 Run 详情。"""
        try:
            run = repository.get_run(task_id, run_id)
            return _run_view(run)
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

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
            raise HTTPException(404, error.message) from error

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
            raise HTTPException(404, error.message) from error

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
            raise HTTPException(404, error.message) from error

    @router.get("/tasks/{task_id}/runs/{run_id}/artifacts/{artifact_key}")
    def download_artifact(task_id: str, run_id: str, artifact_key: str):
        """下载产物文件。"""
        try:
            index = repository.read_json(
                repository.run_dir(task_id, run_id) / "artifacts" / "index.json"
            )
            item = index.get("artifacts", {}).get(artifact_key)
            if not item or item.get("status") != "succeeded":
                raise HTTPException(404, "产物不可用")
            path = (
                repository.run_dir(task_id, run_id)
                / "artifacts"
                / str(item["relative_path"])
            )
            if not path.is_file():
                raise HTTPException(404, "产物文件不存在")
            return FileResponse(path, filename=path.name)
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/tasks/{task_id}/runs/{run_id}/artifacts/{artifact_key}/content")
    def artifact_content(task_id: str, run_id: str, artifact_key: str):
        """获取产物内容（JSON 或文本）。"""
        try:
            index = repository.read_json(
                repository.run_dir(task_id, run_id) / "artifacts" / "index.json"
            )
            item = index.get("artifacts", {}).get(artifact_key)
            if not item:
                raise HTTPException(404, "产物不存在")
            path = (
                repository.run_dir(task_id, run_id)
                / "artifacts"
                / str(item["relative_path"])
            )
            if not path.exists():
                raise HTTPException(404, "产物文件不存在")
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
            raise HTTPException(404, error.message) from error

    # ── Events ──────────────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/runs/{run_id}/events")
    def get_events(task_id: str, run_id: str, after: int = 0):
        """获取事件列表。"""
        try:
            items = telemetry.read_events(task_id, run_id, after)
            return {
                "items": items,
                "next_cursor": items[-1]["sequence"] if items else after,
            }
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    # ── Logs ──────────────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/runs/{run_id}/logs")
    def get_logs(
        task_id: str,
        run_id: str,
        level: str = "",
        component: str = "",
        stage: str = "",
    ):
        """获取日志列表。"""
        try:
            path = (
                repository.run_dir(task_id, run_id)
                / "observability"
                / "logs.jsonl"
            )
            repository.get_run(task_id, run_id)
            items = (
                []
                if not path.exists()
                else [
                    json.loads(line)
                    for line in path.read_text(encoding="utf-8").splitlines()
                    if line
                ]
            )
            return {
                "items": [
                    item
                    for item in items
                    if (not level or item.get("level") == level)
                    and (not component or item.get("component") == component)
                    and (not stage or item.get("stage") == stage)
                ]
            }
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

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
            raise HTTPException(404, error.message) from error

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
            raise HTTPException(404, error.message) from error

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
            raise HTTPException(404, error.message) from error

    @router.get("/tasks/{task_id}/runs/{run_id}/diagnostics/{filename}")
    def download_diagnostics(task_id: str, run_id: str, filename: str):
        """下载诊断包。"""
        if (
            not filename.startswith("diagnostic-")
            or not filename.endswith(".zip")
            or "/" in filename
        ):
            raise HTTPException(400, "诊断包名称无效")
        try:
            repository.get_run(task_id, run_id)
            path = (
                repository.run_dir(task_id, run_id) / "diagnostics" / filename
            )
            if not path.is_file():
                raise HTTPException(404, "诊断包不存在")
            return FileResponse(
                path, media_type="application/zip", filename=filename
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

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
            raise HTTPException(404, "成片尚未生成")
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
