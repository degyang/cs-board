"""P5 legacy/native separation contract tests; no render or task migration."""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from csboard.application.commands import MountainCommands
from csboard.application.legacy_bridge import LegacyJobBridge
from csboard.domain.errors import DomainError


def _legacy_infographic() -> dict:
    return {"id": "old-1", "task_name": "legacy info", "status": "queued",
            "reference_mode": "infographic", "job_type": "generate"}


@pytest.mark.parametrize("marker", (
    {"reference_mode": "infographic"}, {"job_type": "infographic"},
    {"pipeline_id": "infographic-remotion-v8"},
))
def test_legacy_infographic_is_v8_read_projection_only(tmp_path: Path, marker: dict) -> None:
    job = {**_legacy_infographic(), **marker}
    link = LegacyJobBridge(tmp_path).sync("old-1", job)
    assert link.pipeline_id == "infographic-remotion-v8"
    commands = MountainCommands(tmp_path)
    for invoke in (
        lambda: commands.stage_run(link.task_id, link.run_id, "render-visuals"),
        lambda: commands.stage_retry(link.task_id, link.run_id, "render-visuals"),
        lambda: commands.pipeline_run(link.task_id, link.run_id),
        lambda: commands.pipeline_resume(link.task_id, link.run_id),
    ):
        with pytest.raises(DomainError) as rejected:
            invoke()
        assert rejected.value.code == "LEGACY_READ_ONLY"


def test_native_and_legacy_route_inventory_is_explicit() -> None:
    root = Path(__file__).parents[1]
    native = (root / "webapp/mountain_server.py").read_text(encoding="utf-8")
    legacy = (root / "webapp/mountain_api.py").read_text(encoding="utf-8")
    assert "mountain_task_api" in native and "mountain_capability_api" in native
    tree = ast.parse(native)
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert not any(item == "webapp.mountain_api" or item == "csboard.application.legacy_bridge" for item in imports)
    # The untouched legacy router remains distinguishable and fail-closed for
    # the native engine; it is not a native capability authority.
    assert '"infographic-remotion", "visual_source": "preset", "supported": False' in legacy


def test_native_commands_and_remotion_adapter_have_no_legacy_or_fallback_imports() -> None:
    root = Path(__file__).parents[1]
    forbidden = {"webapp.server", "webapp.mountain_api", "webapp.mountain_stages", "csboard.application.legacy_bridge"}
    for relative in ("csboard/application/commands.py", "csboard/adapters/remotion/renderer_adapter.py"):
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
        imported |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        assert not any(item == banned or item.startswith(banned + ".") for item in imported for banned in forbidden)


def test_clean_native_process_does_not_load_legacy_or_whiteboard_renderer() -> None:
    root = Path(__file__).parents[1]
    probe = """
import json, sys
from csboard.application.commands import MountainCommands
from csboard.adapters.remotion.renderer_adapter import RemotionRendererAdapter
print(json.dumps({name: name in sys.modules for name in (
 'webapp.server', 'webapp.mountain_api', 'webapp.mountain_stages',
 'csboard.application.legacy_bridge')}))
"""
    result = subprocess.run([sys.executable, "-c", probe], cwd=root, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"webapp.server": False, "webapp.mountain_api": False,
                                         "webapp.mountain_stages": False, "csboard.application.legacy_bridge": False}
