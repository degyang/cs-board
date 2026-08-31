from __future__ import annotations

import json
import os
import threading
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
        """获取参考音频元信息"""
        input_dir = self.task_dir(task_id) / "inputs"
        for suffix in (".wav", ".mp3", ".m4a", ".ogg", ".flac"):
            candidate = input_dir / f"reference{suffix}"
            if candidate.is_file():
                return {
                    "uploaded": True,
                    "filename": f"reference{suffix}",
                    "content_type": f"audio/{suffix.lstrip('.')}",
                    "size_bytes": candidate.stat().st_size,
                }
        return None

    def commit_inputs(
        self,
        task_id: str,
        request_data: dict,
        preparation: dict,
        visual_anchor_enabled: bool,
        staging_path: Path | None = None,
        reference_filename: str | None = None,
    ) -> None:
        """原子提交：request + task preparation + reference。

        使用备份和锁保证任一失败时恢复原状态。
        """
        with self.task_lock(task_id):
            task_dir = self.task_dir(task_id)
            input_dir = task_dir / "inputs"
            input_dir.mkdir(parents=True, exist_ok=True)

            # 备份旧文件
            request_bak = task_dir / "request.json.bak"
            task_bak = task_dir / "task.json.bak"
            old_ref_backup = None

            # 读取旧状态
            request_path = task_dir / "request.json"
            task_path = task_dir / "task.json"

            old_request = None
            if request_path.exists():
                old_request = self._read_json(request_path)
                # 备份旧 request
                request_path.rename(request_bak)

            old_task = None
            if task_path.exists():
                old_task = self._read_json(task_path)
                # 备份旧 task
                task_path.rename(task_bak)

            # 备份旧 reference（如果有新 reference 且旧 reference 存在）
            old_reference_path = None
            if old_request and old_request.get("reference_audio"):
                old_ref_path = task_dir / old_request["reference_audio"]
                if old_ref_path.exists() and staging_path:
                    old_ref_backup = task_dir / f"{old_ref_path.name}.bak"
                    old_ref_path.rename(old_ref_backup)
                    old_reference_path = old_ref_path

            try:
                # 写入新 reference（如果有）
                if staging_path and staging_path.exists():
                    suffix = Path(reference_filename or "reference.wav").suffix.lower() or ".wav"
                    target = input_dir / f"reference{suffix}"
                    staging_path.rename(target)

                # 写入新 request
                self._write_json(request_path, request_data)

                # 更新 task preparation
                if old_task:
                    task_data = old_task.copy()
                else:
                    task_data = self._read_json(task_path) if task_path.exists() else {}
                task_data["script_preparation"] = preparation
                task_data["visual_anchor_enabled"] = visual_anchor_enabled
                self._write_json(task_path, task_data)

                # 成功：清理备份文件
                request_bak.unlink(missing_ok=True)
                task_bak.unlink(missing_ok=True)
                if old_ref_backup:
                    old_ref_backup.unlink(missing_ok=True)

            except Exception:
                # 失败：恢复旧状态
                if request_bak.exists():
                    request_bak.rename(request_path)
                if task_bak.exists():
                    task_bak.rename(task_path)
                if old_ref_backup and old_ref_backup.exists() and old_reference_path:
                    old_ref_backup.rename(old_reference_path)
                # 清理 staging
                if staging_path and staging_path.exists():
                    staging_path.unlink(missing_ok=True)
                raise

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
