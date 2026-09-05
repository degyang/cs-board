"""Locate external tools (Python, Node, FFmpeg, …)."""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


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


# P3a consumes this read-only projection.  It intentionally does not invoke
# node, Remotion, ffmpeg, or a browser: existence and the lock relationship
# are bootstrap prerequisites, not a render health check.
def bootstrap_diagnostics(
    root: Path,
    *,
    which: Callable[[str], str | None] = shutil.which,
    environ: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Return public-safe, deterministic Remotion toolchain diagnostics.

    No diagnostic contains a resolved path, command line, package contents, or
    environment value.  ``REMOTION_BROWSER_EXECUTABLE`` is the only browser
    source accepted because it is the browser source consumed by render.mjs.
    """
    environment = os.environ if environ is None else environ
    renderer = root / "video_renderer"
    script = renderer / "render.mjs"
    lockfile = renderer / "package-lock.json"

    def check(component: str, ready: bool, reason_code: str | None = None) -> dict[str, Any]:
        return {"component": component, "ready": bool(ready), "reason_code": reason_code}

    result = [
        check("node", bool(which("node")), "NODE_NOT_FOUND"),
        check("render-script", script.is_file(), "RENDER_SCRIPT_MISSING"),
    ]
    lock_data: dict[str, Any] | None = None
    try:
        value = json.loads(lockfile.read_text(encoding="utf-8"))
        lock_data = value if isinstance(value, dict) else None
    except (OSError, ValueError, json.JSONDecodeError):
        lock_data = None
    result.append(check("lockfile", lock_data is not None, "LOCKFILE_INVALID"))

    # Require each renderer dependency to be declared by the root package and
    # physically pinned in the npm lockfile, rather than trusting node_modules.
    locked = False
    if lock_data is not None:
        try:
            declared = lock_data["packages"][""]["dependencies"]
            packages = lock_data["packages"]
            names = ("@remotion/bundler", "@remotion/renderer", "remotion")
            locked = all(isinstance(declared.get(name), str) and declared[name]
                         and isinstance(packages.get(f"node_modules/{name}"), dict)
                         and packages[f"node_modules/{name}"].get("version")
                         for name in names)
        except (AttributeError, KeyError, TypeError):
            locked = False
    result.append(check("locked-remotion", locked, "REMOTION_NOT_INSTALLED"))

    browser = environment.get("REMOTION_BROWSER_EXECUTABLE", "")
    # An empty or inaccessible configured executable is fail-closed.  Do not
    # report its value: it may be an operator-specific filesystem path.
    result.append(check("remotion-browser", bool(browser) and Path(browser).is_file() and os.access(browser, os.X_OK),
                        "BROWSER_UNAVAILABLE"))
    result.extend((
        check("ffmpeg", bool(which("ffmpeg")), "FFMPEG_NOT_FOUND"),
        check("ffprobe", bool(which("ffprobe")), "FFPROBE_NOT_FOUND"),
    ))
    return result
