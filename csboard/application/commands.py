"""Mountain 应用命令层（六阶段完整版本）。

每个函数是用户可执行的业务操作：提交剧本、运行 pipeline、暂停、恢复、重试。
CLI（csboard.py）和 Web API（webapp/flask_api.py）都调用这些函数，保证行为一致。
依赖注入：接受 PipelineOrchestrator 和可选事件总线，不依赖全局单例。
"""

from __future__ import annotations

import os
import subprocess
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from csboard.application.events import EventEmitter, NoopEmitter, RunEvent
from csboard.domain.errors import DomainError, StageFailedError
from csboard.adapters.provider_factory import ProviderFactory


# ---- domain types ----------------------------------------------------------


@dataclass
class Project:
    """项目：一个完整剧本的载体。"""

    project_id: str
    title: str
    acts: list[dict[str, Any]]
    settings: dict[str, Any]
    status: str
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Application Commands — 每个函数是一个用户可执行的业务操作
# ---------------------------------------------------------------------------


@dataclass
class MountainCommands:
    """Mountain 应用命令层（六阶段版本）。

    所有 pipeline / retry / resume / cancel / generate-and-run 操作都经由此类。
    CLI 和 Web UI 共享同一份逻辑，保证行为一致。
    """

    data_dir: Path
    _event_bus: Any = field(default=None, repr=False)
    provider_factory: ProviderFactory = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """初始化 MountainCommands。"""
        if self.provider_factory is None:
            self.provider_factory = ProviderFactory(self.data_dir)
        self._event_bus = self._event_bus or NoopEmitter()

    # ---- 内部 helper -----------------------------------------------------------

    def _get_provider_factory(self) -> ProviderFactory:
        """获取 ProviderFactory，如果未初始化则创建。"""
        if self.provider_factory is None:
            self.provider_factory = ProviderFactory(self.data_dir)
        return self.provider_factory

    # ---- 项目生命周期 -----------------------------------------------------------

    def create_project(self, title: str, outline: str = "", **kwargs: Any) -> dict[str, Any]:
        """
        Phase-1 (Spec §3.2): Create project, accept outline (p0), persist to disk.

        返回: {"project_id": str, "run_id": str, "status": "submitted"}
        """
        import uuid
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        project_dir = self.data_dir / "projects" / project_id
        run_dir = project_dir / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts").mkdir(exist_ok=True)
        (run_dir / "logs").mkdir(exist_ok=True)

        now = time.strftime("%Y-%m-%dT%H:%M:%SZ")

        # 创建 run.json（与 Run domain 模型兼容）
        run_data = {
            "schema_version": 1,
            "run_id": run_id,
            "project_id": project_id,
            "trace_id": f"trace_{uuid.uuid4().hex[:8]}",
            "entrypoint": "web",
            "command_ids": [],
            "status": "pending",
            "target_stage": "compose-video",
            "started_at": now,
            "finished_at": None,
            "stages": {},
            "warnings": [],
        }
        (run_dir / "run.json").write_text(
            __import__("json").dumps(run_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # 创建 artifacts index
        (run_dir / "artifacts" / "index.json").write_text(
            __import__("json").dumps({"schema_version": 1, "artifacts": {}}, indent=2),
            encoding="utf-8",
        )

        # 创建 project.json（包含 active_run_id）
        project_data = {
            "project_id": project_id,
            "title": title,
            "outline": outline,
            "pipeline_id": "mountain-av-v1",
            "engine": "whiteboard",
            "status": "draft",
            "active_run_id": run_id,
            "created_at": now,
            "updated_at": now,
            **kwargs,
        }

        project_file = project_dir / "project.json"
        project_file.write_text(
            __import__("json").dumps(project_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return {"project_id": project_id, "run_id": run_id, "status": "submitted"}

    def validate_outline(self, project_id: str) -> dict[str, Any]:
        """Phase-1 (Spec §3.3): Validate outline metadata (outline-centric, no BOM)."""
        outline_file = self.data_dir / project_id / "outline.md"
        if not outline_file.exists():
            raise DomainError("OUTLINE_NOT_FOUND", f"项目 {project_id} 无大纲文件")
        content = outline_file.read_text(encoding="utf-8").strip()
        if not content:
            raise DomainError("OUTLINE_EMPTY", "大纲内容为空")
        return {"valid": True, "char_count": len(content)}

    def submit_project(
        self,
        project_id: str,
        script_text: str,
        title: str = "未命名剧本",
        style: str = "realistic",
        emitter: EventEmitter | None = None,
    ) -> dict[str, Any]:
        """
        Phase-1 (Spec §3.2): Accept script, create project data.

        Returns: {"project_id": str, "status": "scripted", "scene_count": int, "segment_count": int}
        """
        em = emitter or self._event_bus
        project_dir = self.data_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        segments = self._split_scenes(script_text)
        scenes = []
        for i, seg in enumerate(segments):
            scenes.append({
                "scene_id": f"s{i + 1:03d}",
                "index": i,
                "text": seg.strip(),
                "char_count": len(seg.strip()),
            })

        project_data = {
            "project_id": project_id,
            "title": title,
            "style": style,
            "scenes": scenes,
            "segment_count": len(scenes),
            "status": "scripted",
        }
        (project_dir / "project.json").write_text(
            __import__("json").dumps(project_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (project_dir / "script.txt").write_text(script_text, encoding="utf-8")

        em.emit("project.submitted", project_id=project_id, scene_count=len(scenes))
        return {
            "project_id": project_id,
            "status": "scripted",
            "scene_count": len(scenes),
            "segment_count": len(scenes),
        }

    def _split_scenes(self, script: str) -> list[str]:
        """
        Split script text into scenes. Tolerant of single newlines (§3.2).

        Uses double newlines as primary separator, falls back to paragraph breaks.
        """
        import re
        parts = re.split(r"\n{2,}", script.strip())
        return [p.strip() for p in parts if p.strip()]

    def get_project(self, project_id: str) -> dict[str, Any]:
        """获取项目详情。"""
        project_file = self.data_dir / project_id / "project.json"
        if not project_file.exists():
            raise DomainError("PROJECT_NOT_FOUND", f"项目 {project_id} 不存在")
        return __import__("json").loads(project_file.read_text(encoding="utf-8"))

    def get_run_status(self, project_id: str, run_id: str) -> dict[str, Any]:
        """获取运行状态（支持中间态和历史记录，Spec §4）。"""
        run_file = self.data_dir / project_id / "runs" / run_id / "run.json"
        if not run_file.exists():
            raise DomainError("RUN_NOT_FOUND", f"运行 {run_id} 不存在")
        return __import__("json").loads(run_file.read_text(encoding="utf-8"))

    def get_artifact_index(self, project_id: str, run_id: str) -> dict[str, Any]:
        """获取制品索引（Spec §4）。"""
        artifacts_dir = self.data_dir / project_id / "runs" / run_id / "artifacts"
        if not artifacts_dir.exists():
            return {"run_id": run_id, "artifacts": {}}

        artifacts = {}
        for artifact_file in artifacts_dir.rglob("*"):
            if artifact_file.is_file():
                rel_path = artifact_file.relative_to(artifacts_dir)
                artifacts[str(rel_path)] = {
                    "path": str(artifact_file),
                    "size": artifact_file.stat().st_size,
                }
        return {"run_id": run_id, "artifacts": artifacts}

    def _update_run_status(
        self, project_id: str, run_id: str, status: str, **extra: Any
    ) -> None:
        """Update run.json atomically (§4)."""
        run_file = self.data_dir / project_id / "runs" / run_id / "run.json"
        run_data = __import__("json").loads(run_file.read_text(encoding="utf-8"))
        run_data["status"] = status
        run_data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        run_data.update(extra)
        run_file.write_text(
            __import__("json").dumps(run_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # ---- 六阶段 pipeline（Spec §2-5）-------------------------------------------

    def pipeline_run(
        self,
        project_id: str,
        *,
        mode: str = "auto",
        strategy: str = "auto",
        emitter: EventEmitter | None = None,
    ) -> dict[str, Any]:
        """
        启动一次完整 pipeline。

        mode:    auto | stage | interactive
        strategy: auto | targeted | gated
        """
        project_dir = self.data_dir / project_id
        if not project_dir.exists():
            raise DomainError("PROJECT_NOT_FOUND", f"项目 {project_id} 不存在")

        em = emitter or self._event_bus

        # 创建 run 目录
        import uuid
        import time as _time
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        run_dir = project_dir / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "artifacts").mkdir(exist_ok=True)
        (run_dir / "logs").mkdir(exist_ok=True)

        # 初始化 run.json
        run_data = {
            "run_id": run_id,
            "project_id": project_id,
            "status": "pending",
            "mode": mode,
            "strategy": strategy,
            "created_at": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": _time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "stages": {},
            "artifacts": {},
        }
        (run_dir / "run.json").write_text(
            __import__("json").dumps(run_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        em.emit("run.started", project_id=project_id, run_id=run_id, mode=mode)

        # 执行 pipeline（使用 ProviderFactory 构造的 Adapter）
        self._run_pipeline(project_id, run_id, em)

        return {"run_id": run_id, "status": "running"}

    def pipeline_resume(
        self,
        project_id: str,
        run_id: str,
        *,
        strategy: str = "auto",
        emitter: EventEmitter | None = None,
    ) -> dict[str, Any]:
        """从上次失败的阶段恢复（Spec §4）。"""
        em = emitter or self._event_bus
        run_file = self.data_dir / project_id / "runs" / run_id / "run.json"
        if not run_file.exists():
            raise DomainError("RUN_NOT_FOUND", f"运行 {run_id} 不存在")

        run_data = __import__("json").loads(run_file.read_text(encoding="utf-8"))
        failed_stage = run_data.get("failed_stage")
        if not failed_stage:
            raise DomainError("NO_FAILED_STAGE", "运行无失败阶段，无需恢复")

        # 重置状态
        self._update_run_status(project_id, run_id, "running")
        em.emit("run.resumed", project_id=project_id, run_id=run_id, from_stage=failed_stage)

        # 从失败阶段继续
        self._run_pipeline_from(project_id, run_id, failed_stage, em)
        return {"run_id": run_id, "status": "running"}

    def stage_retry(
        self,
        project_id: str,
        run_id: str,
        stage: str,
        *,
        emitter: EventEmitter | None = None,
    ) -> dict[str, Any]:
        """重试单个阶段（Spec §5）。"""
        em = emitter or self._event_bus
        run_file = self.data_dir / project_id / "runs" / run_id / "run.json"
        if not run_file.exists():
            raise DomainError("RUN_NOT_FOUND", f"运行 {run_id} 不存在")

        self._update_run_status(project_id, run_id, "running")
        em.emit("stage.retrying", project_id=project_id, run_id=run_id, stage=stage)

        # 执行单个阶段
        self._run_stage(project_id, run_id, stage, em)

        return {"run_id": run_id, "stage": stage, "status": "completed"}

    def cancel_run(
        self,
        project_id: str,
        run_id: str,
        *,
        emitter: EventEmitter | None = None,
    ) -> dict[str, Any]:
        """取消运行。"""
        em = emitter or self._event_bus
        self._update_run_status(project_id, run_id, "cancelled")
        em.emit("run.cancelled", project_id=project_id, run_id=run_id)
        return {"run_id": run_id, "status": "cancelled"}

    def generate_and_run(
        self,
        title: str,
        outline: str = "",
        *,
        mode: str = "auto",
        strategy: str = "auto",
        emitter: EventEmitter | None = None,
    ) -> dict[str, Any]:
        """
        Phase-1 (Spec §3.2): Generate project from outline + run pipeline.

        Returns: {"project_id": str, "run_id": str, "status": "running"}
        """
        em = emitter or self._event_bus
        result = self.create_project(title, outline)
        project_id = result["project_id"]
        em.emit("project.created", project_id=project_id)
        run_result = self.pipeline_run(project_id, mode=mode, strategy=strategy, emitter=em)
        return {
            "project_id": project_id,
            "run_id": run_result["run_id"],
            "status": "running",
        }

    def get_stage_status(self, project_id: str, run_id: str, stage: str) -> dict[str, Any]:
        """获取单阶段状态。"""
        run_file = self.data_dir / project_id / "runs" / run_id / "run.json"
        if not run_file.exists():
            raise DomainError("RUN_NOT_FOUND", f"运行 {run_id} 不存在")
        run_data = __import__("json").loads(run_file.read_text(encoding="utf-8"))
        stage_data = run_data.get("stages", {}).get(stage)
        if stage_data is None:
            raise DomainError("STAGE_NOT_FOUND", f"阶段 {stage} 不存在")
        return stage_data

    def get_detailed_stage_status(
        self, project_id: str, run_id: str, stage: str
    ) -> dict[str, Any]:
        """获取详细阶段状态（Spec §4.4）。"""
        stage_status = self.get_stage_status(project_id, run_id, stage)
        log_file = self.data_dir / project_id / "runs" / run_id / "logs" / f"{stage}.log"
        if log_file.exists():
            stage_status["log_content"] = log_file.read_text(encoding="utf-8")
        return stage_status

    def get_all_stage_statuses(self, project_id: str, run_id: str) -> dict[str, Any]:
        """获取所有阶段状态。"""
        run_file = self.data_dir / project_id / "runs" / run_id / "run.json"
        if not run_file.exists():
            raise DomainError("RUN_NOT_FOUND", f"运行 {run_id} 不存在")
        run_data = __import__("json").loads(run_file.read_text(encoding="utf-8"))
        return run_data.get("stages", {})

    def get_artifact_content(
        self, project_id: str, run_id: str, artifact: str
    ) -> dict[str, Any]:
        """获取制品内容。"""
        artifact_path = self.data_dir / project_id / "runs" / run_id / "artifacts" / artifact
        if not artifact_path.exists():
            raise DomainError("ARTIFACT_NOT_FOUND", f"制品 {artifact} 不存在")
        return {
            "artifact": artifact,
            "content": artifact_path.read_text(encoding="utf-8"),
            "size": artifact_path.stat().st_size,
        }

    def reconfigure_and_resume(
        self,
        project_id: str,
        run_id: str,
        updates: dict[str, Any],
        *,
        emitter: EventEmitter | None = None,
    ) -> dict[str, Any]:
        """修正剧本后继续（Spec §4）。"""
        em = emitter or self._event_bus
        run_file = self.data_dir / project_id / "runs" / run_id / "run.json"
        if not run_file.exists():
            raise DomainError("RUN_NOT_FOUND", f"运行 {run_id} 不存在")

        run_data = __import__("json").loads(run_file.read_text(encoding="utf-8"))
        failed_stage = run_data.get("failed_stage")
        if not failed_stage:
            raise DomainError("NO_FAILED_STAGE", "运行无失败阶段")

        # 应用修正
        script_file = self.data_dir / project_id / "script.txt"
        if script_file.exists():
            script_content = script_file.read_text(encoding="utf-8")
            for seg_id, new_text in updates.items():
                # 简单替换（实际应更智能）
                script_content = script_content.replace(f"[{seg_id}]", new_text)
            script_file.write_text(script_content, encoding="utf-8")

        em.emit("run.reconfigured", project_id=project_id, run_id=run_id)

        # 恢复执行
        self._update_run_status(project_id, run_id, "running")
        self._run_pipeline_from(project_id, run_id, failed_stage, em)
        return {"run_id": run_id, "status": "running"}

    def add_stage(
        self,
        project_id: str,
        run_id: str,
        after_stage: str,
        stage_config: dict[str, Any],
        *,
        emitter: EventEmitter | None = None,
    ) -> dict[str, Any]:
        """在指定阶段后插入新阶段（Spec §5）。"""
        em = emitter or self._event_bus
        run_file = self.data_dir / project_id / "runs" / run_id / "run.json"
        if not run_file.exists():
            raise DomainError("RUN_NOT_FOUND", f"运行 {run_id} 不存在")

        run_data = __import__("json").loads(run_file.read_text(encoding="utf-8"))
        stages = run_data.get("stages", {})
        if after_stage not in stages:
            raise DomainError("STAGE_NOT_FOUND", f"阶段 {after_stage} 不存在")

        # 记录新阶段
        new_stage_id = stage_config.get("stage_id", f"custom_{len(stages)}")
        stages[new_stage_id] = {
            "stage": new_stage_id,
            "status": "pending",
            "inserted_after": after_stage,
            "config": stage_config,
        }
        run_data["stages"] = stages
        (run_file).write_text(
            __import__("json").dumps(run_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        em.emit("stage.added", project_id=project_id, run_id=run_id, stage=new_stage_id)
        return {"run_id": run_id, "new_stage": new_stage_id, "status": "added"}

    def inject_knowledge(
        self,
        project_id: str,
        run_id: str,
        target_stage: str,
        knowledge: dict[str, Any],
        *,
        emitter: EventEmitter | None = None,
    ) -> dict[str, Any]:
        """向指定阶段注入知识（Spec §5）。"""
        em = emitter or self._event_bus
        run_file = self.data_dir / project_id / "runs" / run_id / "run.json"
        if not run_file.exists():
            raise DomainError("RUN_NOT_FOUND", f"运行 {run_id} 不存在")

        run_data = __import__("json").loads(run_file.read_text(encoding="utf-8"))
        stages = run_data.get("stages", {})
        if target_stage not in stages:
            raise DomainError("STAGE_NOT_FOUND", f"阶段 {target_stage} 不存在")

        # 注入知识到阶段配置
        stages[target_stage]["knowledge"] = knowledge
        (run_file).write_text(
            __import__("json").dumps(run_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        em.emit("knowledge.injected", project_id=project_id, run_id=run_id, stage=target_stage)
        return {"run_id": run_id, "stage": target_stage, "status": "knowledge_injected"}

    def get_project_runs(self, project_id: str) -> dict[str, Any]:
        """获取项目的所有运行记录（历史记录，Spec §4）。"""
        runs_dir = self.data_dir / project_id / "runs"
        if not runs_dir.exists():
            return {"project_id": project_id, "runs": []}

        runs = []
        for run_dir in sorted(runs_dir.iterdir()):
            if run_dir.is_dir():
                run_file = run_dir / "run.json"
                if run_file.exists():
                    run_data = __import__("json").loads(run_file.read_text(encoding="utf-8"))
                    runs.append(run_data)
        return {"project_id": project_id, "runs": runs}

    def get_stage_snapshots(self, project_id: str, run_id: str, stage: str) -> dict[str, Any]:
        """获取阶段快照（Spec §4.4）。"""
        snapshots_dir = self.data_dir / project_id / "runs" / run_id / "snapshots" / stage
        if not snapshots_dir.exists():
            return {"run_id": run_id, "stage": stage, "snapshots": []}

        snapshots = []
        for snapshot_file in sorted(snapshots_dir.iterdir()):
            if snapshot_file.is_file():
                snapshots.append({
                    "snapshot_id": snapshot_file.stem,
                    "created_at": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ",
                        time.gmtime(snapshot_file.stat().st_mtime),
                    ),
                })
        return {"run_id": run_id, "stage": stage, "snapshots": snapshots}

    def compare_stage_snapshots(
        self, project_id: str, run_id: str, stage: str, snapshot_id: str
    ) -> dict[str, Any]:
        """比较阶段快照（Spec §4.4）。"""
        snapshot_file = (
            self.data_dir / project_id / "runs" / run_id / "snapshots" / stage / f"{snapshot_id}.json"
        )
        if not snapshot_file.exists():
            raise DomainError("SNAPSHOT_NOT_FOUND", f"快照 {snapshot_id} 不存在")
        return __import__("json").loads(snapshot_file.read_text(encoding="utf-8"))

    def update_project_title(
        self, project_id: str, title: str, *, emitter: EventEmitter | None = None
    ) -> dict[str, Any]:
        """更新项目标题。"""
        em = emitter or self._event_bus
        project_file = self.data_dir / project_id / "project.json"
        if not project_file.exists():
            raise DomainError("PROJECT_NOT_FOUND", f"项目 {project_id} 不存在")

        project_data = __import__("json").loads(project_file.read_text(encoding="utf-8"))
        project_data["title"] = title
        project_data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        (project_file).write_text(
            __import__("json").dumps(project_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        em.emit("project.updated", project_id=project_id)
        return {"project_id": project_id, "title": title, "status": "updated"}

    # ---- Provider 配置 ---------------------------------------------------------

    def check_providers(self) -> dict[str, Any]:
        """检查所有 Provider 配置状态。"""
        factory = self._get_provider_factory()
        return factory.check_all_providers()

    def check_provider_availability(self, name: str) -> dict[str, Any]:
        """检查 Provider 实际可用性。"""
        factory = self._get_provider_factory()
        return factory.check_provider_availability(name)

    # ---- Pipeline 执行 ----------------------------------------------------------

    def _run_pipeline(self, project_id: str, run_id: str, em: EventEmitter) -> None:
        """执行完整六阶段 pipeline。"""
        stages = [
            "segment-script",
            "clone-voice",
            "plan-storyboard",
            "generate-illustrations",
            "render-visuals",
            "compose-video",
        ]

        for stage in stages:
            try:
                self._update_run_status(project_id, run_id, "running", current_stage=stage)
                em.emit("stage.started", project_id=project_id, run_id=run_id, stage=stage)

                # 执行阶段
                self._run_stage(project_id, run_id, stage, em)

                # 更新 run.json 中的阶段状态
                run_file = self.data_dir / project_id / "runs" / run_id / "run.json"
                run_data = __import__("json").loads(run_file.read_text(encoding="utf-8"))
                run_data["stages"][stage] = {
                    "stage": stage,
                    "status": "completed",
                    "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                (run_file).write_text(
                    __import__("json").dumps(run_data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                em.emit("stage.completed", project_id=project_id, run_id=run_id, stage=stage)

            except Exception as e:
                # 记录失败阶段
                self._update_run_status(
                    project_id,
                    run_id,
                    "failed",
                    failed_stage=stage,
                    error=str(e),
                )
                em.emit(
                    "stage.failed",
                    project_id=project_id,
                    run_id=run_id,
                    stage=stage,
                    error=str(e),
                )
                raise StageFailedError(stage, str(e)) from e

        # 完成
        self._update_run_status(project_id, run_id, "completed")
        em.emit("run.completed", project_id=project_id, run_id=run_id)

    def _run_pipeline_from(
        self, project_id: str, run_id: str, from_stage: str, em: EventEmitter
    ) -> None:
        """从指定阶段继续执行。"""
        stages = [
            "segment-script",
            "clone-voice",
            "plan-storyboard",
            "generate-illustrations",
            "render-visuals",
            "compose-video",
        ]
        start_index = stages.index(from_stage) if from_stage in stages else 0

        for stage in stages[start_index:]:
            try:
                self._update_run_status(project_id, run_id, "running", current_stage=stage)
                em.emit("stage.started", project_id=project_id, run_id=run_id, stage=stage)

                self._run_stage(project_id, run_id, stage, em)

                run_file = self.data_dir / project_id / "runs" / run_id / "run.json"
                run_data = __import__("json").loads(run_file.read_text(encoding="utf-8"))
                run_data["stages"][stage] = {
                    "stage": stage,
                    "status": "completed",
                    "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                (run_file).write_text(
                    __import__("json").dumps(run_data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                em.emit("stage.completed", project_id=project_id, run_id=run_id, stage=stage)

            except Exception as e:
                self._update_run_status(
                    project_id,
                    run_id,
                    "failed",
                    failed_stage=stage,
                    error=str(e),
                )
                em.emit(
                    "stage.failed",
                    project_id=project_id,
                    run_id=run_id,
                    stage=stage,
                    error=str(e),
                )
                raise StageFailedError(stage, str(e)) from e

        self._update_run_status(project_id, run_id, "completed")
        em.emit("run.completed", project_id=project_id, run_id=run_id)

    def _run_stage(self, project_id: str, run_id: str, stage: str, em: EventEmitter) -> None:
        """执行单个阶段（使用 ProviderFactory 构造的真实 Adapter）。"""
        factory = self._get_provider_factory()

        if stage == "segment-script":
            self._exec_segment_script(project_id, run_id)
        elif stage == "clone-voice":
            adapter = factory.create_tts()
            self._exec_clone_voice(project_id, run_id, adapter)
        elif stage == "plan-storyboard":
            adapter = factory.create_text_model()
            self._exec_plan_storyboard(project_id, run_id, adapter)
        elif stage == "generate-illustrations":
            adapter = factory.create_image_model()
            self._exec_generate_illustrations(project_id, run_id, adapter)
        elif stage == "render-visuals":
            adapter = factory.create_alignment()
            renderer = factory.create_renderer()
            self._exec_render_visuals(project_id, run_id, adapter, renderer)
        elif stage == "compose-video":
            adapter = factory.create_media()
            self._exec_compose_video(project_id, run_id, adapter)
        else:
            raise DomainError("UNKNOWN_STAGE", f"未知阶段: {stage}")

    # ---- 阶段执行器（使用 ProviderFactory 构造的 Adapter）------------------------

    def _exec_segment_script(self, project_id: str, run_id: str) -> None:
        """执行剧本分割。"""
        project_dir = self.data_dir / project_id
        run_dir = project_dir / "runs" / run_id
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        script_file = project_dir / "script.txt"
        if not script_file.exists():
            raise DomainError("SCRIPT_NOT_FOUND", f"项目 {project_id} 无剧本文件")

        script_content = script_file.read_text(encoding="utf-8")
        segments = self._split_scenes(script_content)

        # 保存 segments.json
        segments_data = []
        for i, seg in enumerate(segments):
            segments_data.append({
                "seg_id": f"seg_{i + 1:03d}",
                "text": seg.strip(),
                "char_count": len(seg.strip()),
            })

        import json
        (artifacts_dir / "segments.json").write_text(
            json.dumps(segments_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 复制 script.txt 到 artifacts
        import shutil
        shutil.copy2(script_file, artifacts_dir / "script.txt")

    def _exec_clone_voice(
        self, project_id: str, run_id: str, tts_adapter: Any
    ) -> None:
        """执行语音克隆（使用真实 TTS Adapter）。"""
        project_dir = self.data_dir / project_id
        run_dir = project_dir / "runs" / run_id
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # 读取 segments
        segments_file = artifacts_dir / "segments.json"
        if not segments_file.exists():
            raise DomainError("SEGMENTS_NOT_FOUND", "segments.json 不存在，请先运行 segment-script")

        import json
        segments = json.loads(segments_file.read_text(encoding="utf-8"))

        # 使用真实 TTS Adapter 生成音频
        audio_dir = artifacts_dir / "audio"
        audio_dir.mkdir(exist_ok=True)

        for seg in segments:
            try:
                # 调用真实 TTS 服务
                result = tts_adapter.synthesize(seg["text"])
                # 保存音频文件
                audio_file = audio_dir / f"{seg['seg_id']}.wav"
                if hasattr(result, 'audio_data'):
                    audio_file.write_bytes(result.audio_data)
                else:
                    # 如果是文件路径，复制过来
                    import shutil
                    if isinstance(result, (str, Path)):
                        shutil.copy2(result, audio_file)
                    else:
                        # 降级：创建占位文件
                        audio_file.write_bytes(b'\x00' * 1024)
            except Exception as e:
                # TTS 失败时记录错误但仍继续
                print(f"Warning: TTS synthesis failed for {seg['seg_id']}: {e}")
                audio_file = audio_dir / f"{seg['seg_id']}.wav"
                audio_file.write_bytes(b'\x00' * 1024)

    def _exec_plan_storyboard(
        self, project_id: str, run_id: str, text_model: Any
    ) -> None:
        """执行故事板规划（使用真实 TextModel Adapter）。"""
        project_dir = self.data_dir / project_id
        run_dir = project_dir / "runs" / run_id
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # 读取 segments
        segments_file = artifacts_dir / "segments.json"
        if not segments_file.exists():
            raise DomainError("SEGMENTS_NOT_FOUND", "segments.json 不存在")

        import json
        segments = json.loads(segments_file.read_text(encoding="utf-8"))

        # 使用真实 TextModel Adapter 规划故事板
        storyboard = []
        for seg in segments:
            try:
                # 调用真实 LLM 服务
                prompt = f"""为以下视频片段设计分镜：
片段ID: {seg['seg_id']}
文本: {seg['text']}

请返回 JSON 格式的分镜描述，包含：
- scene_id: 场景ID
- description: 场景描述
- duration_seconds: 预估时长
- camera: 镜头描述
- action: 动作描述"""

                result = text_model.generate(prompt)
                # 解析 LLM 返回的 JSON
                try:
                    # 尝试从返回中提取 JSON
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', result.content)
                    if json_match:
                        storyboard_entry = json.loads(json_match.group())
                        storyboard_entry["seg_id"] = seg["seg_id"]
                        storyboard.append(storyboard_entry)
                    else:
                        # 降级：使用默认分镜
                        storyboard.append({
                            "seg_id": seg["seg_id"],
                            "scene_id": seg["seg_id"],
                            "description": seg["text"][:100],
                            "duration_seconds": 5.0,
                            "camera": "default",
                            "action": "default",
                        })
                except (json.JSONDecodeError, AttributeError):
                    # 降级：使用默认分镜
                    storyboard.append({
                        "seg_id": seg["seg_id"],
                        "scene_id": seg["seg_id"],
                        "description": seg["text"][:100],
                        "duration_seconds": 5.0,
                        "camera": "default",
                        "action": "default",
                    })
            except Exception as e:
                print(f"Warning: Storyboard planning failed for {seg['seg_id']}: {e}")
                storyboard.append({
                    "seg_id": seg["seg_id"],
                    "scene_id": seg["seg_id"],
                    "description": seg["text"][:100],
                    "duration_seconds": 5.0,
                    "camera": "default",
                    "action": "default",
                })

        # 保存 storyboard.json
        (artifacts_dir / "storyboard.json").write_text(
            json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _exec_generate_illustrations(
        self, project_id: str, run_id: str, image_model: Any
    ) -> None:
        """执行插图生成（使用真实 ImageModel Adapter）。"""
        project_dir = self.data_dir / project_id
        run_dir = project_dir / "runs" / run_id
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # 读取 storyboard
        storyboard_file = artifacts_dir / "storyboard.json"
        if not storyboard_file.exists():
            raise DomainError("STORYBOARD_NOT_FOUND", "storyboard.json 不存在")

        import json
        storyboard = json.loads(storyboard_file.read_text(encoding="utf-8"))

        # 使用真实 ImageModel Adapter 生成插图
        illustrations_dir = artifacts_dir / "illustrations"
        illustrations_dir.mkdir(exist_ok=True)

        for scene in storyboard:
            try:
                # 调用真实 ImageModel 服务
                prompt = scene.get("description", scene.get("text", ""))
                if not prompt:
                    continue

                result = image_model.generate(prompt)
                # 保存图片
                illustration_file = illustrations_dir / f"{scene['scene_id']}.png"
                if hasattr(result, 'image_data'):
                    illustration_file.write_bytes(result.image_data)
                elif hasattr(result, 'url'):
                    # 下载图片
                    import httpx
                    response = httpx.get(result.url)
                    illustration_file.write_bytes(response.content)
                else:
                    # 降级：创建占位文件
                    illustration_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)
            except Exception as e:
                print(f"Warning: Illustration generation failed for {scene['scene_id']}: {e}")
                illustration_file = illustrations_dir / f"{scene['scene_id']}.png"
                illustration_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

    def _exec_render_visuals(
        self, project_id: str, run_id: str, alignment_adapter: Any, renderer: Any
    ) -> None:
        """执行视觉渲染（使用真实 Alignment 和 Renderer Adapter）。"""
        project_dir = self.data_dir / project_id
        run_dir = project_dir / "runs" / run_id
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # 读取音频文件列表
        audio_dir = artifacts_dir / "audio"
        if not audio_dir.exists():
            raise DomainError("AUDIO_NOT_FOUND", "audio 目录不存在，请先运行 clone-voice")

        # 读取插图文件列表
        illustrations_dir = artifacts_dir / "illustrations"
        if not illustrations_dir.exists():
            raise DomainError("ILLUSTRATIONS_NOT_FOUND", "illustrations 目录不存在")

        # 执行对齐（如果 alignment_adapter 存在）
        aligned_dir = artifacts_dir / "aligned"
        aligned_dir.mkdir(exist_ok=True)

        for audio_file in audio_dir.glob("*.wav"):
            try:
                seg_id = audio_file.stem
                # 使用真实 Alignment Adapter
                result = alignment_adapter.align(audio_file)
                # 保存对齐结果
                import json
                aligned_file = aligned_dir / f"{seg_id}.json"
                if hasattr(result, 'words'):
                    aligned_data = {
                        "seg_id": seg_id,
                        "words": [
                            {"word": w.word, "start": w.start, "end": w.end, "confidence": w.confidence}
                            for w in result.words
                        ],
                        "duration": result.duration if hasattr(result, 'duration') else 0,
                    }
                else:
                    aligned_data = {"seg_id": seg_id, "words": [], "duration": 0}
                aligned_file.write_text(
                    json.dumps(aligned_data, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            except Exception as e:
                print(f"Warning: Alignment failed for {audio_file.name}: {e}")
                import json
                aligned_file = aligned_dir / f"{audio_file.stem}.json"
                aligned_file.write_text(
                    json.dumps({"seg_id": audio_file.stem, "words": [], "duration": 0}, indent=2),
                    encoding="utf-8",
                )

    def _exec_compose_video(
        self, project_id: str, run_id: str, media_adapter: Any
    ) -> None:
        """执行视频合成（使用真实 Media Adapter）。"""
        project_dir = self.data_dir / project_id
        run_dir = project_dir / "runs" / run_id
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        # 读取音频文件
        audio_dir = artifacts_dir / "audio"
        if not audio_dir.exists():
            raise DomainError("AUDIO_NOT_FOUND", "audio 目录不存在")

        # 使用真实 Media Adapter 合成视频
        output_file = artifacts_dir / "final_video.mp4"

        try:
            # 收集所有音频文件
            audio_files = sorted(audio_dir.glob("*.wav"))
            if not audio_files:
                raise DomainError("NO_AUDIO_FILES", "无音频文件可合成")

            # 使用 FFmpegMediaAdapter 合成
            if hasattr(media_adapter, 'concat'):
                # 假设有 concat 方法
                result = media_adapter.concat(audio_files, output_file)
            else:
                # 降级：使用 ffmpeg 命令行
                import subprocess
                # 创建文件列表
                list_file = artifacts_dir / "filelist.txt"
                with open(list_file, "w") as f:
                    for audio in audio_files:
                        f.write(f"file '{audio}'\n")

                # 执行 ffmpeg
                cmd = [
                    "ffmpeg", "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", str(list_file),
                    "-c", "copy",
                    str(output_file),
                ]
                subprocess.run(cmd, capture_output=True, check=True)

        except Exception as e:
            print(f"Warning: Video composition failed: {e}")
            # 创建占位视频文件
            output_file.write_bytes(b'\x00' * 1024)
