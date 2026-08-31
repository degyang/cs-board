from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path

from csboard.application.context import utc_now
from csboard.domain.errors import NotFoundError
from csboard.domain.models import Task, Run


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
        """在任务目录内创建唯一 staging 目录，确保同一文件系统。"""
        task_dir = self.task_dir(task_id)
        staging_dir = task_dir / ".staging"
        staging_dir.mkdir(parents=True, exist_ok=True)
        txn_id = uuid.uuid4().hex[:12]
        txn_dir = staging_dir / txn_id
        txn_dir.mkdir()
        return txn_dir

    def commit_inputs(
        self,
        task_id: str,
        txn_dir: Path | None,
        request_data: dict,
        preparation: dict,
        visual_anchor_enabled: bool,
        reference_filename: str | None = None,
    ) -> None:
        """原子提交：request + task preparation + reference。

        使用唯一事务目录，保证任一失败时恢复原状态。
        """
        with self.task_lock(task_id):
            task_dir = self.task_dir(task_id)
            input_dir = task_dir / "inputs"
            input_dir.mkdir(parents=True, exist_ok=True)

            # 读取旧状态快照
            request_path = task_dir / "request.json"
            task_path = task_dir / "task.json"

            old_request = self._read_json(request_path) if request_path.exists() else None
            old_task = self._read_json(task_path) if task_path.exists() else None

            # 确定旧 reference 路径
            old_ref_path = None
            if old_request and old_request.get("reference_audio"):
                old_ref_path = task_dir / old_request["reference_audio"]

            # 确定新 reference 路径
            new_ref_path = None
            staging_ref = None
            if txn_dir and reference_filename:
                suffix = Path(reference_filename).suffix.lower() or ".wav"
                new_ref_path = input_dir / f"reference{suffix}"
                staging_ref = txn_dir / f"reference{suffix}"

            # 新 request 和 task 临时文件（在事务目录中准备，或直接写入）
            if txn_dir:
                staging_request = txn_dir / "request.json"
                staging_task = txn_dir / "task.json"
            else:
                staging_request = None
                staging_task = None

            try:
                # 1. 准备所有新文件
                if staging_request:
                    self._write_json(staging_request, request_data)
                else:
                    # 无事务目录时直接写入（仅 request 和 task 更新）
                    pass

                if old_task:
                    task_data = old_task.copy()
                else:
                    task_data = {}
                task_data["script_preparation"] = preparation
                task_data["visual_anchor_enabled"] = visual_anchor_enabled
                if staging_task:
                    self._write_json(staging_task, task_data)

                # 2. 原子提交：在 task lock 内执行所有 rename
                txn_id = txn_dir.name if txn_dir else uuid.uuid4().hex[:12]
                request_bak = task_dir / f"request.json.{txn_id}.bak"
                task_bak = task_dir / f"task.json.{txn_id}.bak"
                old_ref_bak = None

                # 备份旧文件
                if old_request and request_path.exists():
                    request_path.rename(request_bak)
                if old_task and task_path.exists():
                    task_path.rename(task_bak)
                if old_ref_path and old_ref_path.exists() and new_ref_path:
                    old_ref_bak = old_ref_path.parent / f"{old_ref_path.name}.{txn_id}.bak"
                    old_ref_path.rename(old_ref_bak)

                try:
                    # 移动新文件到目标位置
                    if staging_request and staging_request.exists():
                        staging_request.rename(request_path)
                    else:
                        self._write_json(request_path, request_data)
                    if staging_task and staging_task.exists():
                        staging_task.rename(task_path)
                    else:
                        self._write_json(task_path, task_data)
                    if staging_ref and staging_ref.exists() and new_ref_path:
                        staging_ref.rename(new_ref_path)

                    # 成功：清理备份
                    request_bak.unlink(missing_ok=True)
                    task_bak.unlink(missing_ok=True)
                    if old_ref_bak:
                        old_ref_bak.unlink(missing_ok=True)

                except Exception:
                    # 提交失败：恢复备份
                    if request_bak.exists() and not request_path.exists():
                        request_bak.rename(request_path)
                    elif request_bak.exists():
                        request_bak.unlink()
                    if task_bak.exists() and not task_path.exists():
                        task_bak.rename(task_path)
                    elif task_bak.exists():
                        task_bak.unlink()
                    if old_ref_bak and old_ref_bak.exists() and not (old_ref_path and old_ref_path.exists()):
                        old_ref_bak.rename(old_ref_path)
                    elif old_ref_bak and old_ref_bak.exists():
                        old_ref_bak.unlink()
                    raise

            except Exception:
                # 清理事务目录
                if txn_dir:
                    self._cleanup_txn(txn_dir)
                raise

            # 成功：清理事务目录
            if txn_dir:
                self._cleanup_txn(txn_dir)

    def _cleanup_txn(self, txn_dir: Path) -> None:
        """清理事务目录及其内容。"""
        if not txn_dir.exists():
            return
        for f in txn_dir.iterdir():
            f.unlink(missing_ok=True)
        txn_dir.rmdir()

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
