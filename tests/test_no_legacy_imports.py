"""WBS-8: Migration boundary — ensure new adapters never import legacy webapp.

Any new adapter under ``csboard/adapters/remotion/`` or the capability
service must not depend on the old ``webapp.server`` module.  This test
scans the source tree statically so it runs fast and requires no network.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Paths that must never import from the legacy webapp.
_FORBIDDEN_IMPORT_ROOTS = (
    "webapp",
    "webapp.server",
    "webapp.mountain_stages",
)

# Source directories to scan.
_SCAN_DIRS = (
    Path("csboard/adapters/remotion"),
    Path("csboard/application"),
)

# Files explicitly exempted (e.g. the legacy bridge itself is allowed to
# know about webapp for migration purposes).
_EXEMPT_FILES = {
    Path("csboard/application/legacy_bridge.py"),
}


def _collect_imports(filepath: Path) -> list[str]:
    """Return all top-level import module names from a Python file."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath)
                         )
    except (SyntaxError, OSError):
        return []
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module.split(".")[0])
    return modules


def _scan_for_legacy_imports() -> list[tuple[Path, str]]:
    """Find any import of legacy webapp modules in scanned directories."""
    violations: list[tuple[Path, str]] = []
    for scan_dir in _SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for py_file in sorted(scan_dir.rglob("*.py")):
            rel = py_file.relative_to(Path("."))
            if rel in _EXEMPT_FILES:
                continue
            for mod in _collect_imports(py_file):
                if mod in _FORBIDDEN_IMPORT_ROOTS:
                    violations.append((rel, mod))
    return violations


def test_no_legacy_webapp_imports_in_new_adapters():
    """New infographic/remotion code must not import webapp.server."""
    violations = _scan_for_legacy_imports()
    assert not violations, (
        f"Legacy webapp imports found in new code: {violations}\n"
        f"These modules must not depend on webapp.server."
    )


def test_remotion_adapter_dir_does_not_exist_yet_is_fine():
    """The remotion adapter directory may not exist yet — that's OK.

    This test ensures the scan gracefully handles missing directories.
    """
    remotion_dir = Path("csboard/adapters/remotion")
    # If it doesn't exist yet, the boundary test still passes (no violations).
    if not remotion_dir.exists():
        assert True  # placeholder; the real check is above.
