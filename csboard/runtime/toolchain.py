"""Locate external tools (Python, Node, FFmpeg, …)."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ToolchainResolver:
    """Resolved paths to every external binary the pipeline needs.

    Use :meth:`auto_detect` for sensible defaults; override individual
    fields for custom installs or desktop shells.
    """

    python: Path
    node: Path
    ffmpeg: Path
    ffprobe: Path
    remotion_renderer: Path

    # ── factory ──────────────────────────────────────────────────────
    @classmethod
    def auto_detect(cls, root: Path) -> ToolchainResolver:
        """Detect tools from the venv, PATH, and well-known locations."""
        venv = root / ".venv"
        if _is_windows():
            python = venv / "Scripts" / "python.exe"
        else:
            python = venv / "bin" / "python"

        return cls(
            python=python if python.exists() else _which_or("python3", python),
            node=_which_or("node", Path("node")),
            ffmpeg=_which_or("ffmpeg", Path("ffmpeg")),
            ffprobe=_which_or("ffprobe", Path("ffprobe")),
            remotion_renderer=root / "video_renderer" / "render.mjs",
        )

    # ── validation ───────────────────────────────────────────────────
    def validate(self) -> list[str]:
        """Return names of missing tools.  Empty list means all ready."""
        missing: list[str] = []
        for label, path in (
            ("python", self.python),
            ("node", self.node),
            ("ffmpeg", self.ffmpeg),
            ("ffprobe", self.ffprobe),
        ):
            if not _is_resolvable(path):
                missing.append(label)
        if not self.remotion_renderer.is_file():
            missing.append("remotion_renderer")
        return missing


# ── helpers ──────────────────────────────────────────────────────────

def _is_windows() -> bool:
    import os
    return os.name == "nt"


def _which_or(name: str, fallback: Path) -> Path:
    found = shutil.which(name)
    return Path(found) if found else fallback


def _is_resolvable(path: Path) -> bool:
    """True if *path* is an absolute existing file or findable on PATH."""
    if path.is_file():
        return True
    return shutil.which(str(path)) is not None
