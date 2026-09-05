"""Tests for infographic-remotion engine wiring in task creation and stage execution (WBS-5).

Covers:
- create_task accepts infographic-remotion when capability is available
- create_task rejects infographic-remotion when capability unavailable
- create_task rejects infographic-remotion without service_resolver
- create_task with whiteboard engine unchanged
- _exec_render_visuals routes to RemotionRendererAdapter for infographic tasks
- _exec_render_visuals routes to ServiceResolver path for whiteboard tasks
- No webapp imports in commands.py changes
"""

from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from csboard.adapters.filesystem import FilesystemTaskRepository
from csboard.application.commands import MountainCommands
from csboard.application.context import CommandContext
from csboard.domain.enums import Engine, Entrypoint
from csboard.domain.errors import DomainError

_CAP_PATCH = "csboard.application.capabilities.CapabilityService"


def _cap_snapshot(supported: bool, reason_code: str | None = None) -> dict:
    """Build a minimal CapabilityService.snapshot() return value."""
    item = {
        "engine": "infographic-remotion",
        "visual_source": "preset",
        "supported": supported,
        "pipeline_id": "mountain-av-v1",
        "reason_code": reason_code,
        "bootstrap_ready": True,
    }
    return {
        "items": [item],
        "providers": {"all_available": supported, "providers": {}, "unavailable": []},
    }


class TestInfographicTaskCreation(unittest.TestCase):
    """Test suite for WBS-5: infographic-remotion engine wiring."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = FilesystemTaskRepository(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    # ── Test 1: create_task accepts infographic-remotion when capability available ──

    def test_create_task_accepts_infographic_engine(self) -> None:
        """create_task with engine=INFOGRAPHIC_REMOTION succeeds when capability is available."""
        commands = MountainCommands(
            self.root,
            repository=self.repository,
        )
        commands.service_resolver = MagicMock()

        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = _cap_snapshot(True)
            result = commands.create_task(
                "信息图任务", "mountain-av-v1", Engine.INFOGRAPHIC_REMOTION,
                context=CommandContext(entrypoint=Entrypoint.CLI, actor_type="internal-test"), internal_test_only=True,
            )

        self.assertTrue(result["ok"])
        self.assertIn("task_id", result)
        task = self.repository.get_task(result["task_id"])
        self.assertEqual(task.engine, Engine.INFOGRAPHIC_REMOTION)

    # ── Test 2: create_task rejects infographic-remotion without capability ──

    def test_create_task_rejects_infographic_without_capability(self) -> None:
        """create_task raises CAPABILITY_NOT_AVAILABLE when infographic-remotion not supported."""
        commands = MountainCommands(
            self.root,
            repository=self.repository,
        )
        commands.service_resolver = MagicMock()

        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = _cap_snapshot(False, "NODE_NOT_FOUND")
            with self.assertRaises(DomainError) as ctx:
                commands.create_task(
                    "不可用信息图", "mountain-av-v1", Engine.INFOGRAPHIC_REMOTION,
                )

        self.assertEqual(ctx.exception.code, "CAPABILITY_NOT_AVAILABLE")
        self.assertIn("NODE_NOT_FOUND", str(ctx.exception))

    # ── Test 3: create_task rejects infographic-remotion without service_resolver ──

    def test_create_task_rejects_infographic_without_service_resolver(self) -> None:
        """create_task raises CAPABILITY_NOT_AVAILABLE when service_resolver is None."""
        commands = MountainCommands(
            self.root,
            repository=self.repository,
        )
        commands.service_resolver = None

        with self.assertRaises(DomainError) as ctx:
            commands.create_task(
                "无SR信息图", "mountain-av-v1", Engine.INFOGRAPHIC_REMOTION,
            )

        self.assertEqual(ctx.exception.code, "CAPABILITY_NOT_AVAILABLE")

    # ── Test 4: create_task with whiteboard engine unchanged ──

    def test_create_task_whiteboard_unchanged(self) -> None:
        """create_task with engine=WHITEBOARD still works as before."""
        commands = MountainCommands(
            self.root,
            repository=self.repository,
        )

        result = commands.create_task("白板任务", "mountain-av-v1", Engine.WHITEBOARD)

        self.assertTrue(result["ok"])
        self.assertIn("task_id", result)
        task = self.repository.get_task(result["task_id"])
        self.assertEqual(task.engine, Engine.WHITEBOARD)

    # ── Test 5: _exec_render_visuals routes to RemotionRendererAdapter ──

    def test_render_visuals_routes_to_remotion_adapter(self) -> None:
        """_exec_render_visuals with infographic task constructs RemotionRendererAdapter."""
        commands = MountainCommands(
            self.root,
            repository=self.repository,
        )
        # Create an infographic task
        commands.service_resolver = MagicMock()
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = _cap_snapshot(True)
            result = commands.create_task(
                "信息图渲染", "mountain-av-v1", Engine.INFOGRAPHIC_REMOTION,
                context=CommandContext(entrypoint=Entrypoint.CLI, actor_type="internal-test"), internal_test_only=True,
            )
        task_id = result["task_id"]
        run_id = result["run_id"]

        # Mock the RemotionRendererAdapter at import location
        mock_adapter_class = MagicMock()
        mock_adapter_instance = MagicMock()
        mock_adapter_class.return_value = mock_adapter_instance

        # Use patch.object on the class to intercept render_visuals call
        captured_renderer = {}

        def mock_render_visuals(self_cmd, tid, rid, renderer, ctx=None):
            captured_renderer["renderer"] = renderer
            return {"ok": True}

        with patch(
            "csboard.adapters.remotion.renderer_adapter.RemotionRendererAdapter",
            mock_adapter_class,
        ), patch.object(
            MountainCommands, "render_visuals", mock_render_visuals,
        ):
            commands._exec_render_visuals(task_id, run_id, CommandContext(entrypoint=Entrypoint.CLI))

        mock_adapter_class.assert_called_once()
        self.assertIs(captured_renderer["renderer"], mock_adapter_instance)

    # ── Test 6: _exec_render_visuals routes to whiteboard adapter ──

    def test_render_visuals_routes_to_whiteboard_adapter(self) -> None:
        """_exec_render_visuals with whiteboard task uses existing ServiceResolver path."""
        commands = MountainCommands(
            self.root,
            repository=self.repository,
        )
        # Create a whiteboard task
        result = commands.create_task("白板渲染", "mountain-av-v1", Engine.WHITEBOARD)
        task_id = result["task_id"]
        run_id = result["run_id"]

        # Set up mock factory and resolver
        mock_factory = MagicMock()
        mock_renderer = MagicMock()
        mock_factory.create_adapter.return_value = mock_renderer
        commands.provider_factory = mock_factory

        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = MagicMock(
            capability="rendering", adapter_type="test",
            config={}, required_secrets=[],
        )
        commands.service_resolver = mock_resolver

        # Use patch.object on the class to intercept render_visuals call
        captured_renderer = {}

        def mock_render_visuals(self_cmd, tid, rid, renderer, ctx=None):
            captured_renderer["renderer"] = renderer
            return {"ok": True}

        with patch.object(
            MountainCommands, "render_visuals", mock_render_visuals,
        ):
            commands._exec_render_visuals(task_id, run_id, CommandContext(entrypoint=Entrypoint.CLI))

        mock_resolver.resolve.assert_called_with("rendering")
        mock_factory.create_adapter.assert_called_once()
        self.assertIs(captured_renderer["renderer"], mock_renderer)

    # ── Test 7: no webapp imports in commands.py ──

    def test_no_webapp_imports_in_commands_changes(self) -> None:
        """AST scan of commands.py for webapp imports — must be clean."""
        commands_path = Path("csboard/application/commands.py")
        tree = ast.parse(commands_path.read_text(encoding="utf-8"), filename=str(commands_path))

        webapp_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("webapp"):
                        webapp_imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("webapp"):
                    webapp_imports.append(f"from {node.module} import ...")

        self.assertEqual(
            webapp_imports, [],
            f"commands.py must not import webapp modules. Found: {webapp_imports}",
        )


if __name__ == "__main__":
    unittest.main()
