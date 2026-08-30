from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from csboard.application.context import new_id, utc_now
from csboard.adapters.filesystem.repository import FilesystemTaskRepository
from csboard.adapters.observability.redactor import DefaultRedactor


class JsonlTelemetry:
    """Append-only, locally queryable telemetry correlated by project/run/trace."""

    def __init__(self, repository: FilesystemTaskRepository, redactor: DefaultRedactor | None = None) -> None:
        self.repository = repository
        self.redactor = redactor or DefaultRedactor({repository.root: "$DATA"})

    def append_event(self, task_id: str, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self._run_dir(task_id, run_id) / "observability" / "events.jsonl"
        record = self._record("event", task_id, run_id, payload)
        with self.repository.task_lock(task_id):
            record["sequence"] = self._next_sequence(path)
            self._append(path, record)
        return record

    def append_log(self, task_id: str, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = self._record("log", task_id, run_id, payload)
        with self.repository.task_lock(task_id):
            self._append(self._run_dir(task_id, run_id) / "observability" / "logs.jsonl", record)
        return record

    def append_audit(self, task_id: str, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        record = self._record("audit", task_id, run_id, payload)
        with self.repository.task_lock(task_id):
            self._append(self._run_dir(task_id, run_id) / "observability" / "audit.jsonl", record)
        return record

    def read_events(self, task_id: str, run_id: str, after_sequence: int = 0) -> list[dict[str, Any]]:
        path = self._run_dir(task_id, run_id) / "observability" / "events.jsonl"
        if not path.exists():
            return []
        return [item for item in self._read_jsonl(path) if int(item.get("sequence", 0)) > after_sequence]

    def export_diagnostic_bundle(self, task_id: str, run_id: str) -> Path:
        run_dir = self._run_dir(task_id, run_id)
        output = run_dir / "diagnostics" / f"diagnostic-{new_id('bundle')}.zip"
        files = [
            self.repository.task_dir(task_id) / "task.json",
            run_dir / "run.json",
            run_dir / "artifacts" / "index.json",
            run_dir / "observability" / "events.jsonl",
            run_dir / "observability" / "logs.jsonl",
            run_dir / "observability" / "audit.jsonl",
        ]
        with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
            for source in files:
                if not source.exists():
                    continue
                relative = source.relative_to(self.repository.task_dir(task_id))
                archive.writestr(str(relative), self._redacted_file(source))
        return output

    def _run_dir(self, task_id: str, run_id: str) -> Path:
        self.repository.get_run(task_id, run_id)
        return self.repository.run_dir(task_id, run_id)

    def _record(self, kind: str, task_id: str, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        run = self.repository.get_run(task_id, run_id)
        return self.redactor.redact({
            "record_id": new_id(kind),
            "record_type": kind,
            "timestamp": utc_now(),
            "task_id": task_id,
            "run_id": run_id,
            "trace_id": run.trace_id,
            **payload,
        })

    @staticmethod
    def _append(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
            output.flush()
            os.fsync(output.fileno())

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    def _next_sequence(self, path: Path) -> int:
        records = self._read_jsonl(path) if path.exists() else []
        return int(records[-1].get("sequence", 0)) + 1 if records else 1

    def _redacted_file(self, source: Path) -> str:
        if source.suffix == ".jsonl":
            return "".join(json.dumps(self.redactor.redact(item), ensure_ascii=False, sort_keys=True) + "\n" for item in self._read_jsonl(source))
        return json.dumps(self.redactor.redact(self.repository.read_json(source)), ensure_ascii=False, indent=2, sort_keys=True)
