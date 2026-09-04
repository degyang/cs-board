from __future__ import annotations

import json
import hashlib
import os
import shutil
import threading
import uuid
from pathlib import Path

from csboard.application.context import utc_now
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.models import Task, Run
from csboard.domain.enums import Engine, Entrypoint, RunStatus, TaskStatus
from csboard.domain.stage_gate import StageGate
from csboard.domain.execution_plan import CANONICAL_STAGES


class FilesystemTaskRepository:
    """Task persistence with canonical task packages and legacy read fallback.

    New tasks live in ``<output-root>/<task-id>``.  The state directory keeps
    only a small, atomic locator record so a subsequent process can resolve a
    package without scanning arbitrary user directories.  Pre-package tasks
    remain readable from ``root/tasks`` and are never migrated implicitly.
    """

    _shared_task_locks: dict[tuple[str, str], threading.RLock] = {}
    _shared_locks_guard = threading.Lock()

    def __init__(self, root: Path, *, project_root: Path | None = None) -> None:
        self.root = root.resolve()
        # Standalone repository callers (including isolated tests) treat their
        # state root as the project root.  Production composition roots pass
        # the actual checkout explicitly.
        self.project_root = (project_root or root).resolve()
        self._locks: dict[str, threading.RLock] = {}
        self._locks_guard = threading.Lock()

    def task_dir(self, task_id: str) -> Path:
        locator = self.package_locator_path(task_id)
        if locator.is_file():
            value = self._read_json(locator)
            package = Path(str(value["package_dir"])).resolve()
            recorded_project = Path(str(value.get("project_root", self.project_root))).resolve()
            try:
                package.relative_to(recorded_project)
            except ValueError as error:
                raise DomainError("TASK_PACKAGE_INVALID", "任务包位置不在允许范围内") from error
            if not self._is_allowed_package_dir(package) and "project_root" not in value:
                raise DomainError("TASK_PACKAGE_INVALID", "任务包位置不在允许范围内")
            return package
        return self.root / "tasks" / task_id

    def package_locator_path(self, task_id: str) -> Path:
        return self.root / ".task-packages" / f"{task_id}.json"

    def list_task_ids(self) -> list[str]:
        """Return package tasks plus legacy tasks without importing either."""
        ids: set[str] = set()
        locators = self.root / ".task-packages"
        if locators.is_dir():
            for path in locators.glob("*.json"):
                try:
                    task_id = str(self._read_json(path)["task_id"])
                    if self.task_dir(task_id).joinpath("task.json").is_file():
                        ids.add(task_id)
                except (OSError, ValueError, KeyError, DomainError):
                    continue
        legacy = self.root / "tasks"
        if legacy.is_dir():
            ids.update(path.parent.name for path in legacy.glob("*/task.json"))
        return sorted(ids)

    def _is_allowed_package_dir(self, path: Path) -> bool:
        try:
            path.relative_to(self.project_root)
            return True
        except ValueError:
            return False

    def resolve_output_root(self, requested_root: str | None) -> Path:
        """Validate the user-facing output root before any package is made.

        A relative root is relative to the project; all roots must remain
        beneath it.  This deliberately fail-closes rather than falling back to
        ``outputs`` when a user supplied path is invalid or unwritable.
        """
        if requested_root is None or not str(requested_root).strip():
            candidate = self.project_root / "outputs"
        elif not isinstance(requested_root, str):
            raise DomainError("OUTPUT_ROOT_INVALID", "输出目录必须是字符串")
        else:
            raw = Path(requested_root).expanduser()
            candidate = raw if raw.is_absolute() else self.project_root / raw
        candidate = candidate.resolve(strict=False)
        try:
            candidate.relative_to(self.project_root)
        except ValueError as error:
            raise DomainError("OUTPUT_ROOT_FORBIDDEN", "输出目录必须位于项目目录内") from error
        existing = candidate
        while not existing.exists() and existing != existing.parent:
            existing = existing.parent
        if not existing.is_dir() or not os.access(existing, os.W_OK | os.X_OK):
            raise DomainError("OUTPUT_ROOT_UNWRITABLE", "输出目录不可写")
        return candidate

    def browse_project_directory(self, requested_path: str | None = None) -> dict:
        """Read-only listing of one project-relative directory.

        The filesystem is never mutated here.  Symlinks are rejected on the
        requested path and omitted from children so they cannot become a
        navigation escape hatch.
        """
        raw = "." if requested_path is None or requested_path == "" else requested_path
        if not isinstance(raw, str):
            raise DomainError("DIRECTORY_INVALID_PATH", "目录路径必须是字符串")
        candidate_path = Path(raw)
        if candidate_path.is_absolute() or any(part == ".." for part in candidate_path.parts):
            raise DomainError("DIRECTORY_FORBIDDEN", "目录路径必须位于项目目录内")
        if any(part in {"", "."} for part in candidate_path.parts) and raw not in {".", ""}:
            # Normalize harmless repeated separators/dot segments only after
            # rejecting parent traversal; the returned path is canonical.
            candidate_path = Path(*[part for part in candidate_path.parts if part not in {"", "."}])
        candidate = (self.project_root / candidate_path)
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as error:
            raise NotFoundError("目录不存在") from error
        except OSError as error:
            raise DomainError("DIRECTORY_READ_ERROR", "目录无法读取") from error
        try:
            resolved.relative_to(self.project_root)
        except ValueError as error:
            raise DomainError("DIRECTORY_FORBIDDEN", "目录路径必须位于项目目录内") from error
        current = self.project_root
        for part in candidate_path.parts:
            current = current / part
            if current.is_symlink():
                raise DomainError("DIRECTORY_FORBIDDEN", "不允许通过符号链接访问目录")
        if not resolved.is_dir():
            raise DomainError("DIRECTORY_NOT_DIRECTORY", "目标路径不是目录")
        try:
            children = []
            for child in resolved.iterdir():
                if child.name.startswith(".") or child.is_symlink() or not child.is_dir():
                    continue
                child_resolved = child.resolve(strict=True)
                try:
                    child_resolved.relative_to(self.project_root)
                except ValueError:
                    continue
                relative = child_resolved.relative_to(self.project_root).as_posix()
                children.append({"name": child.name, "path": relative})
        except OSError as error:
            raise DomainError("DIRECTORY_READ_ERROR", "目录无法读取") from error
        children.sort(key=lambda item: item["name"].casefold())
        relative_current = resolved.relative_to(self.project_root).as_posix() or "."
        return {"path": relative_current, "directories": children}

    def _write_package_locator(self, task_id: str, package_dir: Path) -> None:
        self._write_json(self.package_locator_path(task_id), {
            "schema_version": 1,
            "task_id": task_id,
            "package_dir": str(package_dir),
            "project_root": str(self.project_root),
        })

    def run_dir(self, task_id: str, run_id: str) -> Path:
        return self.task_dir(task_id) / "runs" / run_id

    def task_lock(self, task_id: str) -> threading.RLock:
        # Repository instances are intentionally cheap and are created by
        # separate API/CLI entrypoints. The lock must therefore be shared by
        # canonical root + task, otherwise concurrent instances can interleave
        # the request/task/reference transaction.
        key = (str(self.root), task_id)
        with self._shared_locks_guard:
            return self._shared_task_locks.setdefault(key, threading.RLock())

    def submission_lock(self, submission_id: str) -> threading.RLock:
        """独立锁用于 submission_id 幂等创建序列化。"""
        with self._locks_guard:
            return self._locks.setdefault(f"submission:{submission_id}", threading.RLock())

    def submission_index_path(self, submission_id: str) -> Path:
        return self.root / ".submissions" / f"{submission_id}.json"

    def get_submission(self, submission_id: str) -> dict | None:
        path = self.submission_index_path(submission_id)
        if not path.exists():
            return None
        return self._read_json(path)

    def create_task(self, task: Task, *, output_root: str | None = None) -> None:
        """Atomically create a canonical package for a new task.

        The staging directory is adjacent to the final package to guarantee
        ``replace`` is atomic.  Any failure removes the package and locator;
        no fallback to the volatile state directory is attempted.
        """
        root = self.resolve_output_root(output_root)
        target = root / task.task_id
        with self.task_lock(task.task_id):
            if target.exists() or self.package_locator_path(task.task_id).exists() or (self.root / "tasks" / task.task_id).exists():
                raise FileExistsError(f"Task already exists: {task.task_id}")
            root.mkdir(parents=True, exist_ok=True)
            staging_root = root / ".csboard-staging"
            staging_root.mkdir(exist_ok=True)
            staging = staging_root / uuid.uuid4().hex
            try:
                for child in ("inputs/assets", "inputs/parameters", "runs"):
                    (staging / child).mkdir(parents=True)
                self._write_json(staging / "task.json", task.to_dict())
                self._write_json(staging / "task-package.json", {
                    "schema_version": 1,
                    "task_id": task.task_id,
                    "package_kind": "csboard-task-package",
                    "created_at": task.created_at,
                    "inputs": {"assets_dir": "inputs/assets", "parameters_dir": "inputs/parameters"},
                    "runs_dir": "runs",
                })
                self._package_txn_checkpoint("before_commit", task.task_id)
                os.replace(staging, target)
                self._package_txn_checkpoint("before_locator", task.task_id)
                self._write_package_locator(task.task_id, target)
            except Exception:
                if staging.exists():
                    shutil.rmtree(staging, ignore_errors=True)
                if target.exists():
                    shutil.rmtree(target, ignore_errors=True)
                locator = self.package_locator_path(task.task_id)
                if locator.exists():
                    locator.unlink()
                raise
            finally:
                if staging_root.exists() and not any(staging_root.iterdir()):
                    staging_root.rmdir()

    def _package_txn_checkpoint(self, name: str, task_id: str) -> None:
        """Test hook for package-creation transaction fault injection."""

    def create_task_submission(
        self,
        submission_id: str,
        task: Task,
        run: Run,
        request_signature: str,
        *,
        created_at: str | None = None,
        output_root: str | None = None,
    ) -> dict:
        """为 submission_id 创建新的 task/run 并写入幂等索引，任意失败点都回滚。

        返回：
          {"task_id", "run_id", "trace_id", "created_at"}
        """
        lock = self.submission_lock(submission_id)
        with lock:
            existing = self.get_submission(submission_id)
            if existing:
                if existing.get("request_signature") != request_signature:
                    raise DomainError("SUBMISSION_CONFLICT", "同一 submission_id 已用于其他请求参数")
                return existing

            self._write_submission_checkpoint("before_task")
            self.create_task(task, output_root=output_root)
            try:
                self._write_submission_checkpoint("before_run")
                self.create_run(run)
            except Exception:
                # 回滚：删除 Task，不留孤立索引
                self._delete_task(task.task_id)
                raise

            now = created_at or utc_now()
            index_payload = {
                "submission_id": submission_id,
                "task_id": task.task_id,
                "run_id": run.run_id,
                "trace_id": run.trace_id,
                "request_signature": request_signature,
                "created_at": now,
            }
            try:
                self._write_submission_checkpoint("before_index")
                self._write_json(self.submission_index_path(submission_id), index_payload)
            except Exception:
                self._delete_task(task.task_id)
                raise
            return index_payload

    def _delete_task(self, task_id: str) -> None:
        task_dir = self.task_dir(task_id)
        if task_dir.exists():
            shutil.rmtree(task_dir)
        locator = self.package_locator_path(task_id)
        if locator.exists():
            locator.unlink()

    def _delete_submission_index(self, submission_id: str) -> None:
        path = self.submission_index_path(submission_id)
        if path.exists():
            path.unlink()

    def _write_submission_checkpoint(self, name: str) -> None:
        """测试钩子：子类可覆盖，用于故障注入。"""

    def get_task(self, task_id: str) -> Task:
        path = self.task_dir(task_id) / "task.json"
        if not path.is_file():
            raise NotFoundError("任务不存在")
        return Task.from_dict(self._read_json(path))

    def recovery_metadata(self, task_id: str) -> dict | None:
        """Return sanitized historical-recovery metadata, if present."""
        path = self.task_dir(task_id) / "task-package.json"
        if not path.is_file():
            return None
        value = self._read_json(path).get("recovery")
        return value if isinstance(value, dict) else None

    def final_path(self, task_id: str, run_id: str) -> Path:
        """Resolve a final video through the canonical package repository."""
        canonical = self.run_dir(task_id, run_id) / "artifacts" / "output" / "final.mp4"
        if canonical.is_file():
            return canonical
        return self.run_dir(task_id, run_id) / "final" / "final.mp4"

    def import_partial_historical_final(
        self,
        *,
        task_id: str,
        run_id: str,
        source_file: Path,
        expected_size: int,
        expected_sha256: str,
        authority_refs: list[str],
        missing_evidence: list[str],
        output_root: str | None = None,
    ) -> dict:
        """Import one verified surviving final as an explicitly partial package."""
        source_file = Path(source_file).expanduser()
        if not source_file.is_file():
            raise DomainError("RECOVERY_SOURCE_NOT_FOUND", "来源成片不存在")
        actual_size = source_file.stat().st_size
        if actual_size != expected_size:
            raise DomainError("RECOVERY_SIZE_MISMATCH", "来源成片大小校验失败")
        digest = hashlib.sha256()
        with source_file.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        actual_sha256 = digest.hexdigest()
        if actual_sha256 != expected_sha256:
            raise DomainError("RECOVERY_HASH_MISMATCH", "来源成片 SHA-256 校验失败")
        if not task_id or not run_id or not expected_sha256:
            raise DomainError("VALIDATION_ERROR", "恢复标识和 hash 不能为空")

        output_root = self.resolve_output_root(output_root)
        target = output_root / task_id
        package_file = target / "task-package.json"
        recovery = {
            "recovery_status": "partial",
            "kind": "partial_historical_import",
            "original_task_id": task_id,
            "original_run_id": run_id,
            "source_file": source_file.name,
            "source_size_bytes": actual_size,
            "source_sha256": actual_sha256,
            "authority_references": list(authority_refs),
            "missing_evidence": list(missing_evidence),
        }
        with self.task_lock(task_id):
            if target.exists() or self.package_locator_path(task_id).exists() or (self.root / "tasks" / task_id).exists():
                if package_file.is_file():
                    existing = self._read_json(package_file).get("recovery")
                    if existing == recovery and self.final_path(task_id, run_id).is_file():
                        return {"task_id": task_id, "run_id": run_id, "recovery_status": "partial", "idempotent": True}
                raise DomainError("RECOVERY_TARGET_CONFLICT", "恢复目标已存在且内容不一致")

            now = utc_now()
            task = Task(task_id=task_id, title="昨日任务（部分历史恢复）", summary="基于已验证成片的部分历史导入", pipeline_id="mountain-av-v1", engine=Engine.WHITEBOARD, status=TaskStatus.SUCCEEDED, created_at=now, updated_at=now, active_run_id=run_id)
            run = Run(run_id=run_id, task_id=task_id, trace_id="trace-recovered-" + run_id.removeprefix("run-"), entrypoint=Entrypoint.CLI, command_ids=[], status=RunStatus.SUCCEEDED, target_stage="compose-video", started_at=now, finished_at=now)
            staging_root = output_root / ".csboard-staging"
            staging_root.mkdir(parents=True, exist_ok=True)
            staging = staging_root / uuid.uuid4().hex
            try:
                (staging / "inputs/assets").mkdir(parents=True)
                (staging / "inputs/parameters").mkdir(parents=True)
                run_dir = staging / "runs" / run_id
                for child in ("planning", "audio", "images", "clips", "subtitles", "manifests", "evidence", "final", "artifacts/output"):
                    (run_dir / child).mkdir(parents=True, exist_ok=True)
                self._write_json(staging / "task.json", task.to_dict())
                self._write_json(staging / "task-package.json", {"schema_version": 1, "task_id": task_id, "package_kind": "csboard-task-package", "created_at": now, "recovery": recovery, "missing_evidence": list(missing_evidence)})
                self._write_json(run_dir / "run.json", run.to_dict())
                self._write_json(run_dir / "artifacts/index.json", {"schema_version": 1, "artifacts": {"final.video": {"relative_path": "output/final.mp4", "sha256": actual_sha256, "size_bytes": actual_size, "producer_stage": "compose-video", "status": "verified"}}})
                staged_final = run_dir / "artifacts/output/final.mp4.partial"
                shutil.copyfile(source_file, staged_final)
                if staged_final.stat().st_size != expected_size:
                    raise DomainError("RECOVERY_SIZE_MISMATCH", "导入中成片大小校验失败")
                staged_final.replace(run_dir / "artifacts/output/final.mp4")
                os.replace(staging, target)
                self._write_package_locator(task_id, target)
            except Exception:
                if staging.exists():
                    shutil.rmtree(staging, ignore_errors=True)
                if target.exists():
                    shutil.rmtree(target, ignore_errors=True)
                locator = self.package_locator_path(task_id)
                if locator.exists():
                    locator.unlink()
                raise
            finally:
                if staging_root.exists() and not any(staging_root.iterdir()):
                    staging_root.rmdir()
        return {"task_id": task_id, "run_id": run_id, "recovery_status": "partial", "idempotent": False}

    def save_task(self, task: Task) -> None:
        with self.task_lock(task.task_id):
            current = self.get_task(task.task_id)
            task.revision = current.revision + 1
            task.updated_at = utc_now()
            self._write_json(self.task_dir(task.task_id) / "task.json", task.to_dict())

    def create_run(self, run: Run) -> None:
        target = self.run_dir(run.task_id, run.run_id)
        with self.task_lock(run.task_id):
            if not (self.task_dir(run.task_id) / "task.json").is_file():
                raise NotFoundError("任务不存在")
            if target.exists():
                raise FileExistsError(f"Run already exists: {run.run_id}")
            for child in ("planning", "audio", "images", "clips", "subtitles", "manifests", "evidence", "final", "artifacts", "media", "observability", "diagnostics"):
                (target / child).mkdir(parents=True, exist_ok=True)
            self._write_json(target / "run.json", run.to_dict())
            self._write_json(target / "artifacts" / "index.json", {"schema_version": 1, "artifacts": {}})

    def get_run(self, task_id: str, run_id: str) -> Run:
        path = self.run_dir(task_id, run_id) / "run.json"
        if not path.is_file():
            raise NotFoundError("运行记录不存在")
        return Run.from_dict(self._read_json(path))

    def save_run(self, run: Run) -> None:
        with self.task_lock(run.task_id):
            self._write_json(self.run_dir(run.task_id, run.run_id) / "run.json", run.to_dict())

    def get_gates(self, task_id: str, run_id: str) -> list[StageGate]:
        run = self.get_run(task_id, run_id)
        path = self.run_dir(task_id, run_id) / "gates.json"
        if not path.exists(): return [StageGate.initial(task_id, run_id, run.trace_id, stage) for stage in CANONICAL_STAGES]
        saved = {item["stage_id"]: StageGate.from_dict(item) for item in self._read_json(path).get("items", [])}
        return [saved.get(stage, StageGate.initial(task_id, run_id, run.trace_id, stage)) for stage in CANONICAL_STAGES]

    def save_gates(self, task_id: str, run_id: str, gates: list[StageGate]) -> None:
        with self.task_lock(task_id):
            self.get_run(task_id, run_id)
            self._write_json(self.run_dir(task_id, run_id) / "gates.json", {"schema_version": 1, "items": [gate.to_dict() for gate in gates]})

    def replace_gate(self, task_id: str, run_id: str, stage: str, expected_revision: int, replacement: StageGate) -> None:
        """CAS replacement plus append-only decision history under one task lock."""
        with self.task_lock(task_id):
            gates = self.get_gates(task_id, run_id)
            current = next(item for item in gates if item.stage_id == stage)
            if current.revision != expected_revision:
                raise RuntimeError("GATE_REVISION_CONFLICT")
            history = self.run_dir(task_id, run_id) / "gate-history" / stage / f"{replacement.revision}.json"
            self._write_json(history, replacement.to_dict())
            self._write_json(self.run_dir(task_id, run_id) / "gates.json", {"schema_version": 1, "items": [(replacement if item.stage_id == stage else item).to_dict() for item in gates]})

    def save_request(self, task_id: str, data: dict) -> None:
        """原子写入 request.json"""
        with self.task_lock(task_id):
            self._write_json(self.task_dir(task_id) / "request.json", data)

    def get_request(self, task_id: str) -> dict | None:
        """读取 request.json，不存在返回 None"""
        path = self.task_dir(task_id) / "request.json"
        if not path.exists():
            return None
        return self._read_json(path)

    def save_input_file(self, task_id: str, filename: str, data: bytes) -> Path:
        """保存输入文件到 inputs/ 目录，返回相对路径"""
        input_dir = self.task_dir(task_id) / "inputs"
        with self.task_lock(task_id):
            input_dir.mkdir(parents=True, exist_ok=True)
            target = input_dir / filename
            temporary = target.with_suffix(f"{target.suffix}.partial")
            temporary.write_bytes(data)
            temporary.replace(target)
        return Path(f"inputs/{filename}")

    def get_input_audio(self, task_id: str) -> dict | None:
        """获取参考音频元信息（从 manifest 读取）"""
        request = self.get_request(task_id)
        if not request or not request.get("reference_audio"):
            return None
        ref_path = self.task_dir(task_id) / request["reference_audio"]
        if not ref_path.exists():
            return None
        return {
            "uploaded": True,
            "filename": ref_path.name,
            "content_type": f"audio/{ref_path.suffix.lstrip('.')}",
            "size_bytes": ref_path.stat().st_size,
        }

    def create_staging(self, task_id: str) -> Path:
        """在任务目录内创建唯一 staging 目录，确保同一文件系统。

        调用前必须验证 task_id 存在。
        """
        task_dir = self.task_dir(task_id)
        if not task_dir.exists():
            raise FileNotFoundError(f"Task {task_id} 不存在")
        staging_dir = task_dir / ".staging"
        staging_dir.mkdir(parents=True, exist_ok=True)
        txn_id = uuid.uuid4().hex[:12]
        txn_dir = staging_dir / txn_id
        txn_dir.mkdir()
        return txn_dir

    def commit_inputs(
        self,
        task_id: str,
        txn_dir: Path,
        request_data: dict,
        preparation: dict,
        visual_anchor_enabled: bool,
        reference_filename: str | None = None,
        preserve_reference: bool = False,
        execution_plan: dict | None = None,
    ) -> None:
        """原子提交：request + task preparation + reference。

        在 task_lock 内完成：读取当前状态、准备最终数据、备份、安装、回滚和清理。
        preserve_reference=True 时在锁内从当前已提交状态保留 reference。
        """
        task_dir = self.task_dir(task_id)
        if not task_dir.exists():
            raise FileNotFoundError(f"Task {task_id} 不存在")

        with self.task_lock(task_id):
            # 在锁内读取当前状态
            request_target = task_dir / "request.json"
            task_target = task_dir / "task.json"

            # 如果需要保留 reference，在锁内读取当前已提交的 reference
            if preserve_reference and not reference_filename:
                current_request = self._read_json(request_target) if request_target.exists() else {}
                current_ref = current_request.get("reference_audio")
                if current_ref:
                    request_data = {**request_data, "reference_audio": current_ref}

            # 在事务目录中准备所有新文件
            tmp_request = txn_dir / "request.json"
            self._write_json(tmp_request, request_data)

            tmp_task = txn_dir / "task.json"
            existing_task = self._read_json(task_target) if task_target.exists() else {}
            existing_task["script_preparation"] = preparation
            existing_task["visual_anchor_enabled"] = visual_anchor_enabled
            self._write_json(tmp_task, existing_task)

            if execution_plan is not None:
                request_data = {**request_data, "execution_plan": execution_plan}
                self._write_json(tmp_request, request_data)

            # 准备 reference（如果有）
            tmp_ref: Path | None = None
            if reference_filename:
                suffix = Path(reference_filename).suffix.lower() or ".wav"
                staging_ref = txn_dir / f"reference{suffix}"
                if staging_ref.exists():
                    tmp_ref = staging_ref

            # 查找旧 reference 路径
            old_request_data = self._read_json(request_target) if request_target.exists() else {}
            old_ref_relative = old_request_data.get("reference_audio")
            old_ref_path: Path | None = task_dir / old_ref_relative if old_ref_relative else None

            # 调用安装方法（含 checkpoint hook）
            self._install_target(
                task_id=task_id,
                txn_dir=txn_dir,
                tmp_request=tmp_request,
                tmp_task=tmp_task,
                tmp_ref=tmp_ref,
                request_target=request_target,
                task_target=task_target,
                old_ref_path=old_ref_path,
            )

    def _input_txn_checkpoint(self, name: str, context: dict) -> None:
        """事务 checkpoint hook。默认 no-op，测试子类可覆盖以注入故障。

        name: checkpoint 名称，如 "request.after_backup", "task.after_install"
        context: 包含 task_id, txn_id 等信息
        """

    def _install_target(
        self,
        task_id: str,
        txn_dir: Path,
        tmp_request: Path,
        tmp_task: Path,
        tmp_ref: Path | None,
        request_target: Path,
        task_target: Path,
        old_ref_path: Path | None,
    ) -> None:
        """安装所有目标文件。

        事务 ID 从 txn_dir 名称提取。
        回滚策略：先删除本事务已安装的新 target，再恢复旧 backup。
        """
        task_dir = self.task_dir(task_id)
        txn_id = txn_dir.name
        ctx = {"task_id": task_id, "txn_id": txn_id}

        # 记录旧文件用于回滚
        old_request_bak: Path | None = None
        old_task_bak: Path | None = None
        old_ref_bak: Path | None = None

        # 记录已安装的新文件（用于回滚时删除）
        installed_request: Path | None = None
        installed_task: Path | None = None
        installed_ref: Path | None = None

        try:
            # 步骤 1：备份并安装 request
            if request_target.exists():
                old_request_bak = task_dir / f"request.json.{txn_id}.bak"
                request_target.rename(old_request_bak)
            self._input_txn_checkpoint("request.after_backup", ctx)
            tmp_request.rename(request_target)
            installed_request = request_target
            self._input_txn_checkpoint("request.after_install", ctx)

            # 步骤 2：备份并安装 task
            if task_target.exists():
                old_task_bak = task_dir / f"task.json.{txn_id}.bak"
                task_target.rename(old_task_bak)
            self._input_txn_checkpoint("task.after_backup", ctx)
            tmp_task.rename(task_target)
            installed_task = task_target
            self._input_txn_checkpoint("task.after_install", ctx)

            # 步骤 3：备份并安装 reference（如果有）
            if tmp_ref and tmp_ref.exists():
                if old_ref_path and old_ref_path.exists():
                    old_ref_bak = task_dir / f"{old_ref_path.name}.{txn_id}.bak"
                    old_ref_path.rename(old_ref_bak)
                self._input_txn_checkpoint("reference.after_backup", ctx)

                if old_ref_path:
                    if old_ref_path.suffix == tmp_ref.suffix:
                        tmp_ref.rename(old_ref_path)
                        installed_ref = old_ref_path
                    else:
                        new_ref_path = old_ref_path.parent / f"reference{tmp_ref.suffix}"
                        tmp_ref.rename(new_ref_path)
                        installed_ref = new_ref_path
                else:
                    inputs_dir = task_dir / "inputs"
                    inputs_dir.mkdir(exist_ok=True)
                    final_ref = inputs_dir / f"reference{tmp_ref.suffix}"
                    tmp_ref.rename(final_ref)
                    installed_ref = final_ref
                self._input_txn_checkpoint("reference.after_install", ctx)

        except Exception:
            # 回滚：先删除本事务已安装的新 target，再恢复旧 backup
            if installed_request and installed_request.exists():
                installed_request.unlink()
            if installed_task and installed_task.exists():
                installed_task.unlink()
            if installed_ref and installed_ref.exists():
                installed_ref.unlink()

            # 恢复旧 backup
            if old_request_bak and old_request_bak.exists():
                old_request_bak.rename(request_target)
            if old_task_bak and old_task_bak.exists():
                old_task_bak.rename(task_target)
            if old_ref_bak and old_ref_bak.exists():
                if old_ref_path:
                    old_ref_bak.rename(old_ref_path)
                else:
                    old_ref_bak.unlink()

            raise

        else:
            # 成功：清理 backup
            if old_request_bak and old_request_bak.exists():
                old_request_bak.unlink()
            if old_task_bak and old_task_bak.exists():
                old_task_bak.unlink()
            if old_ref_bak and old_ref_bak.exists():
                old_ref_bak.unlink()

        finally:
            # 清理事务目录和空 staging
            if txn_dir.exists():
                shutil.rmtree(txn_dir, ignore_errors=True)
            staging_dir = task_dir / ".staging"
            if staging_dir.exists() and not any(staging_dir.iterdir()):
                staging_dir.rmdir()

    def read_json(self, path: Path) -> dict:
        return self._read_json(path)

    def write_json(self, path: Path, value: dict) -> None:
        self._write_json(path, value)

    @staticmethod
    def _read_json(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
        with temporary.open("w", encoding="utf-8") as output:
            json.dump(value, output, ensure_ascii=False, indent=2, sort_keys=True)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
