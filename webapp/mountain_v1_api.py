"""Mountain v1 API — 纯净的 /api/v1 端点。

不依赖 legacy mountain_stages、legacy_execution_id 或 127.0.0.1:8000。
所有操作通过 MountainCommands 和 PipelineOrchestrator 完成。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from csboard.adapters.filesystem import FilesystemProjectRepository
from csboard.adapters.observability import JsonlTelemetry
from csboard.adapters.provider_factory import ProviderFactory
from csboard.adapters.secrets import mask_secret
from csboard.application.commands import MountainCommands
from csboard.application.context import CommandContext
from csboard.domain.enums import Engine, Entrypoint
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.provider_types import PROVIDER_PROFILES


def mountain_v1_router(data_dir: Path) -> APIRouter:
    """创建 /api/v1 路由器。

    所有端点直接调用 MountainCommands，不依赖 legacy 系统。
    """
    repository = FilesystemProjectRepository(data_dir)
    telemetry = JsonlTelemetry(repository)
    provider_factory = ProviderFactory(data_dir)
    router = APIRouter(prefix="/api/v1", tags=["mountain-v1"])

    def _commands() -> MountainCommands:
        """创建 MountainCommands 实例。"""
        return MountainCommands(data_dir, provider_factory=provider_factory)

    def _context() -> CommandContext:
        """创建 Web 入口的 CommandContext。"""
        return CommandContext(entrypoint=Entrypoint.WEB)

    # ── Capability ──────────────────────────────────────────────────

    @router.get("/capabilities")
    def capabilities():
        """返回支持的引擎/视觉来源组合。"""
        availability = provider_factory.check_all_availability()
        all_available = availability["all_available"]
        return {
            "items": [
                {
                    "engine": "whiteboard",
                    "visual_source": "preset",
                    "supported": all_available,
                    "pipeline_id": "mountain-av-v1",
                    "reason_code": None if all_available else "CAPABILITY_NOT_AVAILABLE",
                },
                {
                    "engine": "whiteboard",
                    "visual_source": "custom-reference",
                    "supported": False,
                    "reason_code": "CAPABILITY_NOT_AVAILABLE",
                },
                {
                    "engine": "infographic-remotion",
                    "visual_source": "preset",
                    "supported": False,
                    "reason_code": "CAPABILITY_NOT_AVAILABLE",
                },
            ],
            "providers": availability,
        }

    # ── Provider Configuration ────────────────────────────────────────

    @router.get("/providers")
    def list_providers():
        """列出所有 Provider 配置状态。"""
        provider_status = provider_factory.check_all_providers()
        availability = provider_factory.check_all_availability()
        return {
            "providers": {
                name: {
                    "profile": provider_factory.get_profile(name).to_dict() if provider_factory.get_profile(name) else PROVIDER_PROFILES[name].to_dict(),
                    "config_status": provider_status["providers"].get(name, {}),
                    "availability": availability["providers"].get(name, {}),
                }
                for name in provider_status["providers"]
            },
            "all_configured": provider_status["all_configured"],
            "all_available": availability["all_available"],
        }

    @router.get("/providers/{provider_name}")
    def get_provider(provider_name: str):
        """获取 Provider Profile 配置。"""
        if provider_name not in PROVIDER_PROFILES:
            raise HTTPException(404, f"Provider '{provider_name}' 不存在")
        profile = provider_factory.get_profile(provider_name)
        if profile is None:
            raise HTTPException(404, f"Provider '{provider_name}' 不存在")
        config_status = provider_factory.check_provider(provider_name)
        availability = provider_factory.check_provider_availability(provider_name)
        return {
            "name": provider_name,
            "profile": profile.to_dict(),
            "config": profile.config,
            "config_status": config_status,
            "availability": availability,
        }

    @router.put("/providers/{provider_name}/config")
    def update_provider_config(provider_name: str, payload: dict = Body(...)):
        """更新 Provider Profile 非敏感配置。"""
        if provider_name not in PROVIDER_PROFILES:
            raise HTTPException(404, f"Provider '{provider_name}' 不存在")

        # 禁止敏感字段
        forbidden_keys = {"api_key", "token", "secret", "password", "credential"}
        for key in payload:
            if key.lower() in forbidden_keys or any(f in key.lower() for f in forbidden_keys):
                raise HTTPException(400, f"不允许更新敏感字段: {key}")

        # 检查未知字段（仅允许 profile 默认 config 中已声明的 key）
        default_profile = PROVIDER_PROFILES[provider_name]
        allowed_keys = set(default_profile.config.keys())
        unknown_keys = set(payload.keys()) - allowed_keys
        if unknown_keys:
            raise HTTPException(400, {
                "code": "UNKNOWN_FIELDS",
                "message": f"不允许更新未知字段: {', '.join(sorted(unknown_keys))}",
                "allowed": sorted(allowed_keys),
            })

        try:
            provider_factory.update_profile_config(provider_name, payload)
            profile = provider_factory.get_profile(provider_name)
            return {"ok": True, "provider": provider_name, "config": profile.config if profile else {}}
        except ValueError as e:
            raise HTTPException(400, str(e)) from e

    @router.post("/providers/{provider_name}/secrets")
    def set_provider_secret(provider_name: str, payload: dict = Body(...)):
        """设置 Provider 的 secret。"""
        if provider_name not in PROVIDER_PROFILES:
            raise HTTPException(404, f"Provider '{provider_name}' 不存在")
        profile = PROVIDER_PROFILES[provider_name]
        secret_key = payload.get("key")
        secret_value = payload.get("value")
        if not secret_key or not secret_value:
            raise HTTPException(400, "key 和 value 不能为空")
        if secret_key not in profile.required_secrets and secret_key not in profile.optional_secrets:
            raise HTTPException(400, f"Provider '{provider_name}' 不支持 secret '{secret_key}'")
        full_key = f"{profile.provider_type.value}_{secret_key}"
        provider_factory.secret_store.set(full_key, secret_value)
        return {"ok": True, "provider": provider_name, "key": secret_key}

    @router.get("/providers/{provider_name}/secrets")
    def get_provider_secrets(provider_name: str):
        """获取 Provider 的 secret 状态（不返回实际值）。"""
        if provider_name not in PROVIDER_PROFILES:
            raise HTTPException(404, f"Provider '{provider_name}' 不存在")
        profile = PROVIDER_PROFILES[provider_name]
        secrets = {}
        for secret_key in profile.required_secrets + profile.optional_secrets:
            full_key = f"{profile.provider_type.value}_{secret_key}"
            value = provider_factory.secret_store.get(full_key)
            secrets[secret_key] = {
                "configured": value is not None,
                "masked_value": mask_secret(value) if value else None,
            }
        return {"provider": provider_name, "secrets": secrets}

    @router.delete("/providers/{provider_name}/secrets/{secret_key}")
    def delete_provider_secret(provider_name: str, secret_key: str):
        """删除 Provider 的 secret。"""
        if provider_name not in PROVIDER_PROFILES:
            raise HTTPException(404, f"Provider '{provider_name}' 不存在")
        profile = PROVIDER_PROFILES[provider_name]
        full_key = f"{profile.provider_type.value}_{secret_key}"
        if not provider_factory.secret_store.has(full_key):
            raise HTTPException(404, f"Secret '{secret_key}' 不存在")
        provider_factory.secret_store.delete(full_key)
        return {"ok": True, "provider": provider_name, "key": secret_key}

    # ── Project ──────────────────────────────────────────────────────

    @router.post("/projects")
    def create_project(payload: dict = Body(...)):
        """创建新项目。"""
        try:
            title = str(payload.get("title", ""))
            engine = Engine(payload.get("engine", "whiteboard"))
            pipeline_id = payload.get("pipeline_id", "mountain-av-v1")
            return _commands().create_project(
                title, pipeline_id, engine, context=_context()
            )
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @router.get("/projects")
    def list_projects(limit: int = 50):
        """列出项目。"""
        items = []
        projects_dir = data_dir / "projects"
        if projects_dir.exists():
            for path in sorted(projects_dir.glob("*/project.json"), reverse=True)[
                : max(1, min(limit, 100))
            ]:
                try:
                    items.append(repository.get_project(path.parent.name).to_dict())
                except NotFoundError:
                    continue
        return {"items": items}

    @router.get("/projects/{project_id}")
    def get_project(project_id: str):
        """获取项目详情。"""
        try:
            project = repository.get_project(project_id)
            run = (
                repository.get_run(project_id, project.active_run_id)
                if project.active_run_id
                else None
            )
            return _project_detail_view(project, run)
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    # ── Input Upload ──────────────────────────────────────────────────

    @router.post("/projects/{project_id}/inputs")
    async def upload_inputs(
        project_id: str,
        script: str = Form(...),
        reference: UploadFile | None = File(None),
        style: str = Form("极简粗线简笔白板风"),
        include_subtitles: bool = Form(True),
        pen_text: str = Form(""),
        stroke_detail: str = Form("detailed"),
    ):
        """上传项目输入（文案和参考音频）。

        reference 可选：首次保存必须提供；后续编辑文案/参数时可省略，保留已有音频。
        """
        try:
            repository.get_project(project_id)
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

        if len(script.strip()) < 10:
            raise HTTPException(400, "文案至少需要 10 个字")

        input_dir = repository.project_dir(project_id) / "inputs"

        # 首次保存必须提供参考音频
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
            # 无新文件时，检查是否已有音频
            has_audio = any(
                (input_dir / f"reference{ext}").is_file()
                for ext in (".wav", ".mp3", ".m4a", ".ogg", ".flac")
            )
            if not has_audio:
                raise HTTPException(400, "首次保存必须提供参考音频")

        # 保存 request.json（新 Project request）
        request_data = {
            "script": script.strip(),
            "reference_audio": str(target),
            "style": style,
            "include_subtitles": include_subtitles,
            "pen_text": pen_text[:12],
            "stroke_detail": stroke_detail
            if stroke_detail in {"light", "standard", "detailed", "full"}
            else "detailed",
        }
        request_path = repository.project_dir(project_id) / "request.json"
        request_path.write_text(
            json.dumps(request_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return {"ok": True, "project_id": project_id, "input_saved": True}

    @router.get("/projects/{project_id}/inputs")
    def get_inputs(project_id: str):
        """读取已保存的任务制作输入。"""
        try:
            repository.get_project(project_id)
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

        request_path = repository.project_dir(project_id) / "request.json"
        if not request_path.exists():
            return {
                "project_id": project_id,
                "saved": False,
                "inputs": None,
                "reference_audio": {"uploaded": False, "filename": None, "content_type": None, "size_bytes": None},
            }

        request_data = json.loads(request_path.read_text(encoding="utf-8"))

        # 查找已保存的参考音频文件
        input_dir = repository.project_dir(project_id) / "inputs"
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

        return {
            "project_id": project_id,
            "saved": True,
            "inputs": {
                "script": request_data.get("script", ""),
                "style": request_data.get("style", "极简粗线简笔白板风"),
                "include_subtitles": request_data.get("include_subtitles", True),
                "pen_text": request_data.get("pen_text", ""),
                "stroke_detail": request_data.get("stroke_detail", "detailed"),
            },
            "reference_audio": audio_meta,
        }

    # ── Run Operations ──────────────────────────────────────────────────

    @router.post("/projects/{project_id}/runs/{run_id}/start")
    def start_run(project_id: str, run_id: str, policy: str = "auto"):
        """启动标准流程。"""
        try:
            # 检查 request.json 是否存在
            request_path = repository.project_dir(project_id) / "request.json"
            if not request_path.exists():
                raise HTTPException(400, "请先上传文案与参考音频")

            # 检查 Provider 实际可用性（配置 + 连接测试）
            availability = provider_factory.check_all_availability()
            if not availability["all_available"]:
                # 构建结构化错误信息
                unavailable_details = []
                for name, status in availability["providers"].items():
                    if not status["available"]:
                        unavailable_details.append({
                            "provider": name,
                            "error_code": status.get("error_code"),
                            "suggestion": status.get("suggestion"),
                        })
                raise HTTPException(
                    400,
                    {
                        "code": "CAPABILITY_NOT_AVAILABLE",
                        "message": "Provider 服务不可用",
                        "unavailable": availability["unavailable"],
                        "details": unavailable_details,
                    },
                )

            # 通过 Pipeline 启动
            return _commands().pipeline_run(
                project_id, run_id, policy, context=_context()
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error

    @router.post("/projects/{project_id}/runs/{run_id}/cancel")
    def cancel_run(project_id: str, run_id: str):
        """取消运行。"""
        try:
            run = repository.get_run(project_id, run_id)
            # 直接更新 Run 状态为 cancelled
            from csboard.domain.enums import RunStatus
            run.status = RunStatus.CANCELLED
            repository.save_run(run)
            telemetry.append_event(
                project_id, run_id, {"event_type": "RunCancelled"}
            )
            return {"ok": True, "status": "cancelled"}
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.post("/projects/{project_id}/runs/{run_id}/retry")
    def retry_run(project_id: str, run_id: str):
        """重试失败的运行。"""
        try:
            return _commands().pipeline_resume(
                project_id, run_id, context=_context()
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error

    # ── Stage Operations ──────────────────────────────────────────────────

    @router.post("/projects/{project_id}/runs/{run_id}/stages/{stage}/run")
    def run_stage(project_id: str, run_id: str, stage: str):
        """运行指定阶段。"""
        try:
            return _commands().pipeline_run(
                project_id, run_id, "targeted", stage, _context()
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error

    @router.post("/projects/{project_id}/runs/{run_id}/stages/{stage}/retry")
    def retry_stage(
        project_id: str,
        run_id: str,
        stage: str,
        unit_id: str = None,
        visual_id: str = None,
    ):
        """重试指定阶段。"""
        try:
            return _commands().stage_retry(
                project_id, run_id, stage, unit_id, visual_id, _context()
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error

    # ── Pipeline Operations ──────────────────────────────────────────────────

    @router.post("/projects/{project_id}/runs/{run_id}/pipeline/run")
    def pipeline_run(
        project_id: str,
        run_id: str,
        policy: str = "auto",
        target_stage: str = None,
    ):
        """运行 Pipeline。"""
        try:
            return _commands().pipeline_run(
                project_id, run_id, policy, target_stage, _context()
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error

    @router.post("/projects/{project_id}/runs/{run_id}/pipeline/resume")
    def pipeline_resume(project_id: str, run_id: str, policy: str = "auto"):
        """恢复 Pipeline。"""
        try:
            return _commands().pipeline_resume(
                project_id, run_id, policy, _context()
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error
        except DomainError as error:
            raise HTTPException(400, {"code": error.code, "message": error.message}) from error

    # ── Run Status ──────────────────────────────────────────────────────

    @router.get("/projects/{project_id}/runs/{run_id}")
    def get_run(project_id: str, run_id: str):
        """获取 Run 详情。"""
        try:
            run = repository.get_run(project_id, run_id)
            return _run_view(run)
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/projects/{project_id}/runs/{run_id}/stages")
    def get_stages(project_id: str, run_id: str):
        """获取所有阶段状态。"""
        try:
            run = repository.get_run(project_id, run_id)
            return {
                "items": [
                    {"stage": name, **state.to_dict()}
                    for name, state in run.stages.items()
                ]
            }
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    # ── Voice Units ──────────────────────────────────────────────────────

    @router.get("/projects/{project_id}/runs/{run_id}/units")
    def get_units(project_id: str, run_id: str):
        """获取 Voice Units。"""
        try:
            run_dir = repository.run_dir(project_id, run_id)
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

    @router.get("/projects/{project_id}/runs/{run_id}/artifacts")
    def list_artifacts(project_id: str, run_id: str):
        """列出所有产物。"""
        try:
            run_dir = repository.run_dir(project_id, run_id)
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

    @router.get("/projects/{project_id}/runs/{run_id}/artifacts/{artifact_key}")
    def download_artifact(project_id: str, run_id: str, artifact_key: str):
        """下载产物文件。"""
        try:
            index = repository.read_json(
                repository.run_dir(project_id, run_id) / "artifacts" / "index.json"
            )
            item = index.get("artifacts", {}).get(artifact_key)
            if not item or item.get("status") != "succeeded":
                raise HTTPException(404, "产物不可用")
            path = (
                repository.run_dir(project_id, run_id)
                / "artifacts"
                / str(item["relative_path"])
            )
            if not path.is_file():
                raise HTTPException(404, "产物文件不存在")
            return FileResponse(path, filename=path.name)
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get(
        "/projects/{project_id}/runs/{run_id}/artifacts/{artifact_key}/content"
    )
    def artifact_content(project_id: str, run_id: str, artifact_key: str):
        """获取产物内容（JSON 或文本）。"""
        try:
            index = repository.read_json(
                repository.run_dir(project_id, run_id) / "artifacts" / "index.json"
            )
            item = index.get("artifacts", {}).get(artifact_key)
            if not item:
                raise HTTPException(404, "产物不存在")
            path = (
                repository.run_dir(project_id, run_id)
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

    @router.get("/projects/{project_id}/runs/{run_id}/events")
    def get_events(project_id: str, run_id: str, after: int = 0):
        """获取事件列表。"""
        try:
            items = telemetry.read_events(project_id, run_id, after)
            return {
                "items": items,
                "next_cursor": items[-1]["sequence"] if items else after,
            }
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    # ── Logs ──────────────────────────────────────────────────────────

    @router.get("/projects/{project_id}/runs/{run_id}/logs")
    def get_logs(
        project_id: str,
        run_id: str,
        level: str = "",
        component: str = "",
        stage: str = "",
    ):
        """获取日志列表。"""
        try:
            path = (
                repository.run_dir(project_id, run_id)
                / "observability"
                / "logs.jsonl"
            )
            repository.get_run(project_id, run_id)
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

    @router.get("/projects/{project_id}/runs/{run_id}/trace")
    def get_trace(project_id: str, run_id: str):
        """获取 Trace 信息。"""
        try:
            run = repository.get_run(project_id, run_id)
            return {
                "trace_id": run.trace_id,
                "command_ids": run.command_ids,
                "entrypoint": run.entrypoint.value,
            }
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    # ── Metrics ──────────────────────────────────────────────────────────

    @router.get("/projects/{project_id}/runs/{run_id}/metrics")
    def get_metrics(project_id: str, run_id: str):
        """获取运行指标。"""
        try:
            run = repository.get_run(project_id, run_id)
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

    @router.post("/projects/{project_id}/runs/{run_id}/diagnostics")
    def export_diagnostics(project_id: str, run_id: str):
        """导出诊断包。"""
        try:
            bundle = telemetry.export_diagnostic_bundle(project_id, run_id)
            return {
                "bundle_id": bundle.stem,
                "download_url": f"/api/v1/projects/{project_id}/runs/{run_id}/diagnostics/{bundle.name}",
            }
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    @router.get("/projects/{project_id}/runs/{run_id}/diagnostics/{filename}")
    def download_diagnostics(project_id: str, run_id: str, filename: str):
        """下载诊断包。"""
        if (
            not filename.startswith("diagnostic-")
            or not filename.endswith(".zip")
            or "/" in filename
        ):
            raise HTTPException(400, "诊断包名称无效")
        try:
            repository.get_run(project_id, run_id)
            path = (
                repository.run_dir(project_id, run_id) / "diagnostics" / filename
            )
            if not path.is_file():
                raise HTTPException(404, "诊断包不存在")
            return FileResponse(
                path, media_type="application/zip", filename=filename
            )
        except NotFoundError as error:
            raise HTTPException(404, error.message) from error

    # ── Final Video ──────────────────────────────────────────────────────

    @router.get("/projects/{project_id}/runs/{run_id}/final")
    def download_final(project_id: str, run_id: str):
        """下载成片。"""
        path = (
            repository.run_dir(project_id, run_id)
            / "artifacts"
            / "output"
            / "final.mp4"
        )
        if not path.exists():
            raise HTTPException(404, "成片尚未生成")
        return FileResponse(
            path, media_type="video/mp4", filename=f"cs-board-{project_id}.mp4"
        )

    # ── Health ──────────────────────────────────────────────────────────

    @router.get("/health")
    def health():
        """服务健康检查。"""
        availability = provider_factory.check_all_availability()
        return {
            "status": "ok" if availability["all_available"] else "degraded",
            "providers": availability,
        }

    # ── Helper Functions ──────────────────────────────────────────────────

    def _project_detail_view(project, run) -> dict[str, Any]:
        """构建 Project 详情视图。"""
        result = {
            "project": project.to_dict(),
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
            # 获取产物列表
            index_path = (
                repository.run_dir(project.project_id, run.run_id)
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
            "project_id": run.project_id,
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
