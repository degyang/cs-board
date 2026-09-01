"""Subprocess lifecycle management with cancellation support."""

from __future__ import annotations

import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from csboard.application.context import utc_now


@dataclass(slots=True)
class ProcessHandle:
    """Handle for a supervised subprocess."""

    process_id: str
    popen: subprocess.Popen[Any]
    started_at: str
    command: list[str]


class ProcessSupervisor:
    """Start, track, and terminate subprocesses.

    Unlike the legacy ``RUNNING_PROCESSES`` dict in ``webapp/server.py``,
    this supervisor is instance-scoped and usable from any entrypoint
    (CLI, Web, Skill).
    """

    def __init__(self) -> None:
        self._handles: dict[str, ProcessHandle] = {}

    # ── public API ───────────────────────────────────────────────────

    def start(
        self,
        command: list[str],
        cwd: Path,
        stdout: Path | None = None,
        stderr: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> ProcessHandle:
        """Launch a subprocess and register it for supervision."""
        options: dict[str, Any] = {"cwd": cwd}
        if stdout is not None:
            stdout.parent.mkdir(parents=True, exist_ok=True)
            options["stdout"] = stdout.open("w", encoding="utf-8")
        if stderr is not None:
            stderr.parent.mkdir(parents=True, exist_ok=True)
            options["stderr"] = stderr.open("w", encoding="utf-8")
        if env is not None:
            options["env"] = env

        popen = subprocess.Popen(command, **options)
        handle = ProcessHandle(
            process_id=uuid.uuid4().hex[:12],
            popen=popen,
            started_at=utc_now(),
            command=list(command),
        )
        self._handles[handle.process_id] = handle
        return handle

    def terminate(self, handle: ProcessHandle, timeout: float = 5.0) -> None:
        """Gracefully stop a process (SIGTERM → wait → SIGKILL)."""
        proc = handle.popen
        if proc.poll() is not None:
            self._handles.pop(handle.process_id, None)
            return

        proc.terminate()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2.0)
        self._handles.pop(handle.process_id, None)

    def cancel_all(self) -> int:
        """Terminate every active process.  Returns count stopped."""
        snapshot = list(self._handles.values())
        for handle in snapshot:
            try:
                self.terminate(handle)
            except OSError:
                pass
        return len(snapshot)

    def active_handles(self) -> list[ProcessHandle]:
        """Return handles whose underlying process is still running."""
        self.cleanup_finished()
        return list(self._handles.values())

    def cleanup_finished(self) -> int:
        """Remove handles for processes that have already exited."""
        dead = [
            pid
            for pid, h in self._handles.items()
            if h.popen.poll() is not None
        ]
        for pid in dead:
            del self._handles[pid]
        return len(dead)
