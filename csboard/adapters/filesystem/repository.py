from __future__ import annotations

import json
import os
import shutil
import threading
import uuid
from pathlib import Path

from csboard.application.context import utc_now
from csboard.domain.errors import NotFoundError
from csboard.domain.models import Task, Run
from csboard.domain.stage_gate import StageGate
from csboard.domain.execution_plan import CANONICAL_STAGES


class FilesystemTaskRepository:
    """Local task persistence with in-process task-level mutual exclusion."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._locks: dict[str, threading.RLock] = {}
        self._locks_guard = threading.Lock()

    def task_dir(self, task_id: str) -> Path:
        return self.root / "tasks" / task_id

    def run_dir(self, task_id: str, run_id: str) -> Path:
        return self.task_dir(task_id) / "runs" / run_id

    def task_lock(self, task_id: str) -> threading.RLock:
        with self._locks_guard:
            return self._locks.setdefault(task_id, threading.RLock())

    def create_task(self, task: Task) -> None:
        target = self.task_dir(task.task_id)
        with self.task_lock(task.task_id):
            if target.exists():
                raise FileExistsError(f"Task already exists: {task.task_id}")
            (target / "inputs").mkdir(parents=True)
            self._write_json(target / "task.json", task.to_dict())

    def get_task(self, task_id: str) -> Task:
        path = self.task_dir(task_id) / "task.json"
        if not path.is_file():
            raise NotFoundError("任务不存在")
        return Task.from_dict(self._read_json(path))

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
            for child in ("artifacts", "media", "observability", "diagnostics"):
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
