from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
import httpx

from csboard.adapters.filesystem import FilesystemTaskRepository
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.commands import MountainCommands
from csboard.application.context import CommandContext
from csboard.domain.enums import Entrypoint
from fastapi import Body
from csboard.domain.errors import DomainError, NotFoundError
from webapp.mountain_stages import clone_voice, submit_legacy_full_pipeline, sync_legacy_state


def mountain_router(data_dir: Path) -> APIRouter:
    repository = FilesystemTaskRepository(data_dir)
    telemetry = JsonlTelemetry(repository)
    router = APIRouter(prefix="/api/mountain", tags=["mountain"])

    @router.get("/capabilities")
    def capabilities():
        return {"items": [
            {"engine": "whiteboard", "visual_source": "preset", "supported": True, "pipeline_id": "mountain-av-v1"},
            {"engine": "whiteboard", "visual_source": "custom-reference", "supported": False, "reason_code": "CAPABILITY_NOT_AVAILABLE"},
            {"engine": "infographic-remotion", "visual_source": "preset", "supported": False, "reason_code": "CAPABILITY_NOT_AVAILABLE"},
        ]}

    @router.post("/tasks")
    def create_task(payload: dict = Body(...)):
        try:
            return MountainCommands(data_dir).create_task(str(payload.get("title", "")), context=CommandContext(entrypoint=Entrypoint.WEB))
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @router.post("/tasks/{task_id}/inputs")
    async def save_inputs(
        task_id: str,
        script: str = Form(...),
        reference: UploadFile = File(...),
        style: str = Form("极简粗线简笔白板风"),
        include_subtitles: bool = Form(True),
        pen_text: str = Form(""),
        stroke_detail: str = Form("detailed"),
    ):
        try:
            repository.get_task(task_id)
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        if len(script.strip()) < 10:
            raise HTTPException(400, "文案至少需要 10 个字")
        suffix = Path(reference.filename or "reference.wav").suffix.lower() or ".wav"
        if suffix not in {".wav", ".mp3", ".m4a", ".ogg", ".flac"}:
            raise HTTPException(400, "参考音频格式不支持")
        input_dir = repository.task_dir(task_id) / "inputs"
        target = input_dir / f"reference{suffix}"
        temporary = target.with_suffix(f"{suffix}.partial")
        with temporary.open("wb") as output:
            while chunk := await reference.read(1024 * 1024):
                output.write(chunk)
        temporary.replace(target)
        repository.write_json(input_dir / "request.json", {
            "script": script.strip(), "reference_path": target.name, "style": style,
            "include_subtitles": include_subtitles, "pen_text": pen_text[:12],
            "stroke_detail": stroke_detail if stroke_detail in {"light", "standard", "detailed", "full"} else "detailed",
        })
        return {"ok": True, "task_id": task_id, "input_saved": True}

    @router.get("/tasks")
    def tasks(limit: int = 50):
        items = []
        for path in sorted((data_dir / "tasks").glob("*/task.json"), reverse=True)[:max(1, min(limit, 100))]:
            try:
                items.append(repository.get_task(path.parent.name).to_dict())
            except NotFoundError:
                continue
        return {"items": items}

    @router.get("/tasks/{task_id}")
    def task(task_id: str):
        try:
            value = repository.get_task(task_id)
            run = repository.get_run(task_id, value.active_run_id) if value.active_run_id else None
            execution = repository.run_dir(task_id, run.run_id) / "execution.json" if run else None
            if run and execution and execution.exists() and run.status.value in {"pending", "running"}:
                legacy_id = str(repository.read_json(execution).get("legacy_execution_id") or "")
                if legacy_id:
                    sync_legacy_state(data_dir, task_id, run.run_id, legacy_id)
                    run = repository.get_run(task_id, run.run_id)
            artifacts = []
            if run:
                index = repository.run_dir(task_id, run.run_id) / "artifacts" / "index.json"
                if index.exists():
                    artifacts = [{"artifact_key": key, **item} for key, item in repository.read_json(index).get("artifacts", {}).items()]
            return {
                "task": value.to_dict(), "active_run": run.to_dict() if run else None,
                "stages": [] if not run else [{"stage": name, **state.to_dict()} for name, state in run.stages.items()],
                "warnings": [] if not run else run.warnings,
                "artifacts": artifacts,
                "trace": None if not run else {"trace_id": run.trace_id, "command_ids": run.command_ids},
            }
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/tasks/{task_id}/runs/{run_id}/units")
    def units(task_id: str, run_id: str):
        try:
            run_dir = repository.run_dir(task_id, run_id)
            plan_path = run_dir / "artifacts" / "planning" / "av-plan.json"
            if not plan_path.exists():
                return {"items": []}
            plan = repository.read_json(plan_path)
            timeline_path = run_dir / "artifacts" / "timing" / "timeline.json"
            timings = {item["unit_id"]: item for item in repository.read_json(timeline_path).get("units", [])} if timeline_path.exists() else {}
            return {"items": [{**unit, "timing": timings.get(unit["unit_id"])} for unit in plan.get("voice_units", [])]}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/tasks/{task_id}/runs/{run_id}/artifacts/{artifact_key}")
    def artifact_download(task_id: str, run_id: str, artifact_key: str):
        try:
            index = repository.read_json(repository.run_dir(task_id, run_id) / "artifacts" / "index.json")
            item = index.get("artifacts", {}).get(artifact_key)
            if not item or item.get("status") != "succeeded":
                raise HTTPException(404, "产物不可用")
            path = repository.run_dir(task_id, run_id) / "artifacts" / str(item["relative_path"])
            if not path.is_file():
                raise HTTPException(404, "产物文件不存在")
            return FileResponse(path, filename=path.name)
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/tasks/{task_id}/runs/{run_id}/events")
    def events(task_id: str, run_id: str, after: int = 0):
        try:
            items = telemetry.read_events(task_id, run_id, after)
            return {"items": items, "next_cursor": items[-1]["sequence"] if items else after}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.post("/tasks/{task_id}/runs/{run_id}/stages/segment-script")
    def segment(task_id: str, run_id: str, payload: dict = Body(...)):
        try:
            return MountainCommands(data_dir).segment_script(task_id, run_id, str(payload.get("script", "")), CommandContext(entrypoint=Entrypoint.WEB))
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @router.post("/tasks/{task_id}/runs/{run_id}/start")
    def start_run(task_id: str, run_id: str):
        try:
            request_path = repository.task_dir(task_id) / "inputs" / "request.json"
            if not request_path.exists():
                raise HTTPException(400, "请先保存文案与参考音频")
            request = repository.read_json(request_path)
            result = MountainCommands(data_dir).segment_script(
                task_id, run_id, str(request["script"]), CommandContext(entrypoint=Entrypoint.WEB)
            )
            result["legacy_execution_id"] = submit_legacy_full_pipeline(data_dir, task_id, run_id)
            return result
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @router.post("/tasks/{task_id}/runs/{run_id}/stages/clone-voice")
    def voice(task_id: str, run_id: str):
        try:
            manifest, timeline = clone_voice(data_dir, task_id, run_id)
            return {"ok": True, "voice_manifest": manifest, "timeline": timeline}
        except (OSError, RuntimeError, ValueError) as error:
            raise HTTPException(500, str(error)) from error

    def legacy_execution(task_id: str, run_id: str) -> str:
        path = repository.run_dir(task_id, run_id) / "execution.json"
        if not path.exists():
            raise HTTPException(409, "该运行尚未提交到执行器")
        return str(repository.read_json(path).get("legacy_execution_id") or "")

    @router.post("/tasks/{task_id}/runs/{run_id}/cancel")
    def cancel(task_id: str, run_id: str):
        legacy_id = legacy_execution(task_id, run_id)
        response = httpx.post(f"http://127.0.0.1:8000/api/jobs/{legacy_id}/cancel", timeout=20)
        response.raise_for_status()
        return {"ok": True, "legacy_execution_id": legacy_id}

    @router.post("/tasks/{task_id}/runs/{run_id}/retry")
    def retry(task_id: str, run_id: str):
        legacy_id = legacy_execution(task_id, run_id)
        response = httpx.post(f"http://127.0.0.1:8000/api/jobs/{legacy_id}/retry", timeout=20)
        response.raise_for_status()
        return {"ok": True, "legacy_execution_id": str(response.json().get("id") or legacy_id)}

    @router.get("/tasks/{task_id}/runs/{run_id}/logs")
    def logs(task_id: str, run_id: str, level: str = "", component: str = "", stage: str = ""):
        try:
            path = repository.run_dir(task_id, run_id) / "observability" / "logs.jsonl"
            repository.get_run(task_id, run_id)
            import json
            items = [] if not path.exists() else [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
            return {"items": [item for item in items if (not level or item.get("level") == level) and (not component or item.get("component") == component) and (not stage or item.get("stage") == stage)]}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/tasks/{task_id}/runs/{run_id}/final")
    def final_video(task_id: str, run_id: str):
        path = repository.run_dir(task_id, run_id) / "artifacts" / "output" / "final.mp4"
        if not path.exists():
            raise HTTPException(404, "成片尚未生成")
        return FileResponse(path, media_type="video/mp4", filename=f"cs-board-{task_id}.mp4")

    @router.post("/tasks/{task_id}/runs/{run_id}/diagnostics")
    def diagnostics(task_id: str, run_id: str):
        try:
            bundle = telemetry.export_diagnostic_bundle(task_id, run_id)
            return {"bundle_id": bundle.stem, "download_url": f"/api/mountain/tasks/{task_id}/runs/{run_id}/diagnostics/{bundle.name}"}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/tasks/{task_id}/runs/{run_id}/diagnostics/{filename}")
    def diagnostic_download(task_id: str, run_id: str, filename: str):
        if not filename.startswith("diagnostic-") or not filename.endswith(".zip") or "/" in filename:
            raise HTTPException(400, "诊断包名称无效")
        try:
            repository.get_run(task_id, run_id)
            path = repository.run_dir(task_id, run_id) / "diagnostics" / filename
            if not path.is_file():
                raise HTTPException(404, "诊断包不存在")
            return FileResponse(path, media_type="application/zip", filename=filename)
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/tasks/{task_id}/runs/{run_id}/trace")
    def trace(task_id: str, run_id: str):
        try:
            run = repository.get_run(task_id, run_id)
            return {"trace_id": run.trace_id, "command_ids": run.command_ids, "entrypoint": run.entrypoint.value}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/tasks/{task_id}/runs/{run_id}/metrics")
    def metrics(task_id: str, run_id: str):
        try:
            run = repository.get_run(task_id, run_id)
            execution = repository.run_dir(task_id, run_id) / "execution.json"
            legacy = {}
            if execution.exists():
                legacy_id = repository.read_json(execution).get("legacy_execution_id")
                job_path = data_dir / "jobs" / str(legacy_id) / "job.json"
                if job_path.exists(): legacy = repository.read_json(job_path)
            return {"run_status": run.status.value, "stage_attempts": {name: state.attempt for name, state in run.stages.items()}, "timings": legacy.get("timings", {}), "progress": legacy.get("progress"), "fallback_count": sum(1 for warning in run.warnings if "FALLBACK" in str(warning.get("code", "")))}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/tasks/{task_id}/runs/{run_id}/health")
    def health(task_id: str, run_id: str):
        try:
            repository.get_run(task_id, run_id)
            from webapp.server import load_config
            config = load_config()
            tts_ok = False
            try:
                tts_ok = httpx.get(config["tts_url"], timeout=5).is_success
            except httpx.HTTPError:
                pass
            return {"tts": {"configured": bool(config.get("tts_url")), "reachable": tts_ok}, "provider": {"configured": bool(config.get("api_key"))}}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    # ── 新增阶段端点 ──────────────────────────────────────────────────

    @router.post("/tasks/{task_id}/runs/{run_id}/stages/plan-storyboard")
    def plan_storyboard(task_id: str, run_id: str):
        try:
            commands = MountainCommands(data_dir)
            # 使用 FakeTextModel，实际生产环境会使用配置的模型
            from csboard.adapters.fakes import FakeTextModel
            text_model = FakeTextModel()
            return commands.plan_storyboard(task_id, run_id, text_model, CommandContext(entrypoint=Entrypoint.WEB))
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @router.post("/tasks/{task_id}/runs/{run_id}/stages/generate-illustrations")
    def generate_illustrations(task_id: str, run_id: str, visual_id: str = None):
        try:
            commands = MountainCommands(data_dir)
            # 使用 FakeImageModel，实际生产环境会使用配置的模型
            from csboard.adapters.fakes import FakeImageModel
            image_model = FakeImageModel()
            return commands.generate_illustrations(task_id, run_id, image_model, visual_id, CommandContext(entrypoint=Entrypoint.WEB))
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @router.post("/tasks/{task_id}/runs/{run_id}/stages/render-visuals")
    def render_visuals(task_id: str, run_id: str):
        try:
            commands = MountainCommands(data_dir)
            # 使用 WhiteboardRendererAdapter
            from csboard.adapters.whiteboard.renderer_adapter import WhiteboardRendererAdapter
            renderer = WhiteboardRendererAdapter()
            return commands.render_visuals(task_id, run_id, renderer, CommandContext(entrypoint=Entrypoint.WEB))
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @router.post("/tasks/{task_id}/runs/{run_id}/stages/compose-video")
    def compose_video(task_id: str, run_id: str):
        try:
            commands = MountainCommands(data_dir)
            # 使用 FakeMedia，实际生产环境会使用 FFmpegMediaAdapter
            from csboard.adapters.fakes import FakeMedia
            media = FakeMedia()
            return commands.compose_video(task_id, run_id, media, CommandContext(entrypoint=Entrypoint.WEB))
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    # ── Pipeline 操作 ──────────────────────────────────────────────────

    @router.post("/tasks/{task_id}/runs/{run_id}/pipeline/run")
    def pipeline_run(
        task_id: str,
        run_id: str,
        policy: str = "auto",
        target_stage: str = None,
    ):
        try:
            commands = MountainCommands(data_dir)
            return commands.pipeline_run(task_id, run_id, policy, target_stage, CommandContext(entrypoint=Entrypoint.WEB))
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @router.post("/tasks/{task_id}/runs/{run_id}/pipeline/resume")
    def pipeline_resume(task_id: str, run_id: str, policy: str = "auto"):
        try:
            commands = MountainCommands(data_dir)
            return commands.pipeline_resume(task_id, run_id, policy, CommandContext(entrypoint=Entrypoint.WEB))
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    # ── Stage 重试 ──────────────────────────────────────────────────

    @router.post("/tasks/{task_id}/runs/{run_id}/stages/{stage}/retry")
    def stage_retry(
        task_id: str,
        run_id: str,
        stage: str,
        unit_id: str = None,
        visual_id: str = None,
    ):
        try:
            commands = MountainCommands(data_dir)
            return commands.stage_retry(task_id, run_id, stage, unit_id, visual_id, CommandContext(entrypoint=Entrypoint.WEB))
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    # ── 产物展示 ──────────────────────────────────────────────────

    @router.get("/tasks/{task_id}/runs/{run_id}/artifacts")
    def list_artifacts(task_id: str, run_id: str):
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

    @router.get("/tasks/{task_id}/runs/{run_id}/artifacts/{artifact_key}/content")
    def artifact_content(task_id: str, run_id: str, artifact_key: str):
        try:
            index = repository.read_json(repository.run_dir(task_id, run_id) / "artifacts" / "index.json")
            item = index.get("artifacts", {}).get(artifact_key)
            if not item:
                raise HTTPException(404, "产物不存在")
            path = repository.run_dir(task_id, run_id) / "artifacts" / str(item["relative_path"])
            if not path.exists():
                raise HTTPException(404, "产物文件不存在")
            if path.suffix == ".json":
                content = json.loads(path.read_text(encoding="utf-8"))
            else:
                content = path.read_text(encoding="utf-8")
            return {"artifact_key": artifact_key, "content": content, "metadata": item}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    return router
