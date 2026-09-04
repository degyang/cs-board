#!/usr/bin/env python3
"""Reject legacy Mountain imports reachable from active product entrypoints."""

from __future__ import annotations

import ast
from pathlib import Path


FORBIDDEN_MODULES = frozenset(
    {"webapp.server", "webapp.mountain_api", "webapp.mountain_stages"}
)


def _module_path(project_root: Path, module: str) -> Path | None:
    relative = Path(*module.split("."))
    module_file = (project_root / relative).with_suffix(".py")
    if module_file.is_file():
        return module_file
    package_init = project_root / relative / "__init__.py"
    return package_init if package_init.is_file() else None


def reachable_imports(project_root: Path, entrypoints: list[Path]) -> list[dict[str, str]]:
    """Return forbidden import edges reachable from the supplied entrypoints."""
    project_root = project_root.resolve()
    pending = [path.resolve() for path in entrypoints]
    seen: set[Path] = set()
    findings: list[dict[str, str]] = []
    while pending:
        source = pending.pop()
        if source in seen or not source.is_file():
            continue
        seen.add(source)
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [
                    f"{node.module}.{alias.name}" if node.module == "webapp" else node.module
                    for alias in node.names
                ]
            else:
                modules = []
            for module in modules:
                local_path = _module_path(project_root, module)
                if local_path is not None:
                    pending.append(local_path)
                forbidden = next(
                    (item for item in FORBIDDEN_MODULES if module == item or module.startswith(item + ".")),
                    None,
                )
                if forbidden:
                    findings.append({"source": str(source), "import": module, "forbidden": forbidden})
    return findings


def active_entrypoints(project_root: Path) -> list[Path]:
    return [
        project_root / "start-webapp.py",
        project_root / "scripts/run_mountain_backend.py",
        project_root / "webapp/mountain_server.py",
        project_root / "cli/csboard.py",
        project_root / "webapp/mountain_task_api.py",
        project_root / "webapp/mountain_asset_api.py",
        project_root / "webapp/mountain_service_api.py",
        project_root / "webapp/mountain_settings_api.py",
    ]


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    findings = reachable_imports(project_root, active_entrypoints(project_root))
    if findings:
        for finding in findings:
            print(f"FORBIDDEN: {finding['source']} imports {finding['import']}")
        return 1
    print("legacy dependency guard: PASS (no forbidden reachable imports)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
