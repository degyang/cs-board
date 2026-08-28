from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from csboard.application.context import utc_now
from csboard.domain.errors import NotFoundError
from csboard.domain.models import Project, Run


class FilesystemProjectRepository:
    """Local project persistence with in-process project-level mutual exclusion."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._locks: dict[str, threading.RLock] = {}
        self._locks_guard = threading.Lock()

    def project_dir(self, project_id: str) -> Path:
        return self.root / "projects" / project_id

    def run_dir(self, project_id: str, run_id: str) -> Path:
        return self.project_dir(project_id) / "runs" / run_id

    def project_lock(self, project_id: str) -> threading.RLock:
        with self._locks_guard:
            return self._locks.setdefault(project_id, threading.RLock())

    def create_project(self, project: Project) -> None:
        target = self.project_dir(project.project_id)
        with self.project_lock(project.project_id):
            if target.exists():
                raise FileExistsError(f"Project already exists: {project.project_id}")
            (target / "inputs").mkdir(parents=True)
            self._write_json(target / "project.json", project.to_dict())

    def get_project(self, project_id: str) -> Project:
        path = self.project_dir(project_id) / "project.json"
        if not path.is_file():
            raise NotFoundError("项目不存在")
        return Project.from_dict(self._read_json(path))

    def save_project(self, project: Project) -> None:
        with self.project_lock(project.project_id):
            current = self.get_project(project.project_id)
            project.revision = current.revision + 1
            project.updated_at = utc_now()
            self._write_json(self.project_dir(project.project_id) / "project.json", project.to_dict())

    def create_run(self, run: Run) -> None:
        target = self.run_dir(run.project_id, run.run_id)
        with self.project_lock(run.project_id):
            if not (self.project_dir(run.project_id) / "project.json").is_file():
                raise NotFoundError("项目不存在")
            if target.exists():
                raise FileExistsError(f"Run already exists: {run.run_id}")
            for child in ("artifacts", "media", "observability", "diagnostics"):
                (target / child).mkdir(parents=True, exist_ok=True)
            self._write_json(target / "run.json", run.to_dict())
            self._write_json(target / "artifacts" / "index.json", {"schema_version": 1, "artifacts": {}})

    def get_run(self, project_id: str, run_id: str) -> Run:
        path = self.run_dir(project_id, run_id) / "run.json"
        if not path.is_file():
            raise NotFoundError("运行记录不存在")
        return Run.from_dict(self._read_json(path))

    def save_run(self, run: Run) -> None:
        with self.project_lock(run.project_id):
            self._write_json(self.run_dir(run.project_id, run.run_id) / "run.json", run.to_dict())

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
