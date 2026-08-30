from __future__ import annotations

from typing import Any, Protocol


class DomainEventSink(Protocol):
    def append_event(self, task_id: str, run_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class DiagnosticLogSink(Protocol):
    def append_log(self, task_id: str, run_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class AuditSink(Protocol):
    def append_audit(self, task_id: str, run_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class Redactor(Protocol):
    def redact(self, payload: Any) -> Any: ...
