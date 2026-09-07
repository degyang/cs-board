"""Centralised path resolution for the Mountain runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    """All filesystem locations the shared kernel needs.

    Construct via :meth:`from_root` rather than building by hand so every
    consumer resolves paths identically.
    """

    root: Path
    state_dir: Path
    jobs_dir: Path
    config_path: Path
    tasks_dir: Path
    temp_dir: Path

    # ── factory ──────────────────────────────────────────────────────
    @classmethod
    def from_root(cls, root: Path) -> RuntimePaths:
        root = root.resolve()
        settings = root / "settings"
        outputs = root / "outputs"
        return cls(
            root=root,
            state_dir=settings,
            jobs_dir=outputs,
            config_path=settings / "config.json",
            tasks_dir=outputs,
            temp_dir=outputs / "temp",
        )

    # ── convenience ──────────────────────────────────────────────────
    def ensure_dirs(self) -> None:
        """Create all managed directories (idempotent)."""
        for path in (
            self.state_dir,
            self.jobs_dir,
            self.tasks_dir,
            self.temp_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
