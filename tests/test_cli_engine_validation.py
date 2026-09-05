"""CLI engine validation — M09 WBS-6 focused tests.

Covers:
- Default whiteboard compatibility (always accepted)
- infographic-remotion accepted when capability is available
- infographic-remotion rejected when capability unavailable (stable error)
- Invalid engine value rejected by argparse
- Snapshot does not leak secrets, paths, or sensitive data
- Task package path isolation (output_root stripped from persisted request)
"""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch, MagicMock

from cli.csboard import EXIT_OK, EXIT_VALIDATION, main
from csboard.adapters.filesystem import FilesystemTaskRepository
from csboard.domain.enums import Engine
from csboard.application.commands import MountainCommands
from csboard.application.context import CommandContext
from csboard.domain.enums import Entrypoint

# CapabilityService is imported locally in commands.create_task; patch the source.
_CAP_PATCH = "csboard.application.capabilities.CapabilityService"


class CliEngineValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = FilesystemTaskRepository(self.root)
        # Patch CLI ROOT so --output-root validation uses the temp dir
        self._root_patcher = patch("cli.csboard.ROOT", self.root)
        self._root_patcher.start()

    def tearDown(self) -> None:
        self._root_patcher.stop()
        self.temporary.cleanup()

    def invoke(self, *args: str) -> tuple[int, dict]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--data-dir", str(self.root), *args])
        return code, json.loads(output.getvalue())

    def _cap_snapshot(self, supported: bool, reason_code: str | None = None) -> dict:
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

    def invoke_internal_infographic(self, title: str) -> tuple[int, dict]:
        """Test-only seam; the public CLI parser has no activation bypass."""
        commands = MountainCommands(self.root, repository=self.repository)
        commands.service_resolver = MagicMock()
        result = commands.create_task(title, engine=Engine.INFOGRAPHIC_REMOTION,
                                      context=CommandContext(entrypoint=Entrypoint.CLI, actor_type="internal-test"),
                                      internal_test_only=True)
        return EXIT_OK, result

    # ── Default whiteboard compatibility ─────────────────────────────

    def test_whiteboard_engine_accepted_by_default(self) -> None:
        code, result = self.invoke("task", "create", "--title", "默认白板任务", "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(result["ok"])
        self.assertIn("task_id", result)

    def test_whiteboard_engine_accepted_explicit(self) -> None:
        code, result = self.invoke(
            "task", "create", "--title", "显式白板", "--engine", "whiteboard", "--json",
        )
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(result["ok"])

    def test_whiteboard_engine_accepted_even_without_service_resolver(self) -> None:
        """Whiteboard never requires capability check."""
        code, result = self.invoke("task", "create", "--title", "无解析器白板", "--json")
        self.assertEqual(code, EXIT_OK)

    # ── infographic-remotion: capability available ───────────────────

    def test_infographic_engine_accepted_when_capability_available(self) -> None:
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = self._cap_snapshot(True)
            code, result = self.invoke_internal_infographic("信息图任务")
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(result["ok"])

    def test_infographic_engine_event_records_engine_value(self) -> None:
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = self._cap_snapshot(True)
            code, result = self.invoke_internal_infographic("事件记录")
        self.assertEqual(code, EXIT_OK)
        task = self.repository.get_task(result["task_id"])
        self.assertEqual(task.engine, Engine.INFOGRAPHIC_REMOTION)

    # ── infographic-remotion: capability unavailable ─────────────────

    def test_infographic_engine_rejected_when_capability_unavailable(self) -> None:
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = self._cap_snapshot(False, "REMOTION_NOT_INSTALLED")
            code, result = self.invoke(
                "task", "create", "--title", "不可用信息图", "--engine", "infographic-remotion", "--json",
            )
        self.assertEqual(code, EXIT_VALIDATION)
        self.assertEqual(result["error"]["code"], "CAPABILITY_NOT_AVAILABLE")
        self.assertIn("infographic-remotion", result["error"]["message"])

    def test_infographic_engine_rejected_when_snapshot_has_no_item(self) -> None:
        """CapabilityService snapshot returns items but none for infographic-remotion."""
        empty_snapshot = {"items": [], "providers": {"all_available": True, "providers": {}, "unavailable": []}}
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = empty_snapshot
            code, result = self.invoke(
                "task", "create", "--title", "缺失引擎项", "--engine", "infographic-remotion", "--json",
            )
        self.assertEqual(code, EXIT_VALIDATION)
        self.assertEqual(result["error"]["code"], "CAPABILITY_NOT_AVAILABLE")

    def test_infographic_engine_rejected_when_service_resolver_is_none(self) -> None:
        """No service resolver → infographic-remotion is never available."""
        from csboard.application.commands import MountainCommands
        from csboard.domain.errors import DomainError
        commands = MountainCommands(
            self.root,
            repository=FilesystemTaskRepository(self.root, project_root=self.root),
        )
        commands.service_resolver = None
        commands.pipeline = MagicMock()
        with self.assertRaises(DomainError) as ctx:
            commands.create_task("无SR", "mountain-av-v1", Engine.INFOGRAPHIC_REMOTION)
        self.assertEqual(ctx.exception.code, "CAPABILITY_NOT_AVAILABLE")

    def test_infographic_error_message_is_sanitized(self) -> None:
        """Error message must not contain internal paths or stack traces."""
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = self._cap_snapshot(False, "NODE_NOT_FOUND")
            code, result = self.invoke(
                "task", "create", "--title", "脱敏测试", "--engine", "infographic-remotion", "--json",
            )
        self.assertEqual(code, EXIT_VALIDATION)
        msg = result["error"]["message"]
        self.assertNotIn("/", msg)
        self.assertNotIn("\\", msg)
        self.assertNotIn("Traceback", msg)
        self.assertNotIn("File \"", msg)
        self.assertIn("NODE_NOT_FOUND", msg)

    # ── Invalid engine ───────────────────────────────────────────────

    def test_invalid_engine_rejected_by_argparse(self) -> None:
        """Argparse rejects unknown engine values before execute()."""
        import subprocess, sys
        completed = subprocess.run(
            [sys.executable, "-m", "cli.csboard",
             "--data-dir", str(self.root), "task", "create",
             "--title", "非法引擎", "--engine", "nonexistent-engine", "--json"],
            text=True, capture_output=True, timeout=30,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("invalid choice", completed.stderr.lower())

    def test_empty_engine_still_uses_default(self) -> None:
        """Omitting --engine defaults to whiteboard."""
        code, result = self.invoke("task", "create", "--title", "省略引擎", "--json")
        self.assertEqual(code, EXIT_OK)
        task = self.repository.get_task(result["task_id"])
        self.assertEqual(task.engine, Engine.WHITEBOARD)

    # ── Snapshot does not leak secrets ───────────────────────────────

    def test_snapshot_does_not_contain_output_root(self) -> None:
        """output_root is stripped from persisted request — never in task package."""
        safe_root = str(self.root / "safe-output")
        code, result = self.invoke(
            "task", "create", "--title", "路径隔离",
            "--output-root", safe_root, "--json",
        )
        self.assertEqual(code, EXIT_OK)
        request_path = self.repository.task_dir(result["task_id"]) / "request.json"
        if request_path.exists():
            request_data = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertNotIn("output_root", request_data)

    def test_snapshot_does_not_contain_secrets_from_request(self) -> None:
        """Even if request JSON contains sensitive fields, they're persisted as-is
        but the task.to_dict() snapshot never includes API keys."""
        request_file = self.root / "request-with-secrets.json"
        request_file.write_text(json.dumps({
            "title": "密钥测试",
            "script": "测试文案内容，足够长以通过验证。",
            "api_key": "sk-should-not-appear-in-output",
            "secret_token": "tok-should-not-appear",
        }), encoding="utf-8")

        code, result = self.invoke(
            "task", "create", "--request", str(request_file), "--json",
        )
        self.assertEqual(code, EXIT_OK)
        task = self.repository.get_task(result["task_id"])
        task_dict = task.to_dict()
        self.assertNotIn("api_key", task_dict)
        self.assertNotIn("secret_token", task_dict)

    def test_task_create_output_is_json_serializable(self) -> None:
        """Output must be valid JSON with no binary or non-serializable content."""
        code, result = self.invoke("task", "create", "--title", "序列化测试", "--json")
        self.assertEqual(code, EXIT_OK)
        serialized = json.dumps(result, ensure_ascii=False)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized["ok"], True)

    # ── Task package path isolation ──────────────────────────────────

    def test_task_package_output_root_isolation(self) -> None:
        """Different output roots produce isolated task packages."""
        code1, r1 = self.invoke(
            "task", "create", "--title", "隔离A",
            "--output-root", str(self.root / "out-a"), "--json",
        )
        code2, r2 = self.invoke(
            "task", "create", "--title", "隔离B",
            "--output-root", str(self.root / "out-b"), "--json",
        )
        self.assertEqual(code1, EXIT_OK)
        self.assertEqual(code2, EXIT_OK)
        self.assertNotEqual(r1["task_id"], r2["task_id"])

    def test_task_engine_persists_in_task_json(self) -> None:
        """Engine value is written to task.json and survives re-read."""
        code, result = self.invoke(
            "task", "create", "--title", "引擎持久化",
            "--engine", "whiteboard", "--json",
        )
        self.assertEqual(code, EXIT_OK)
        task_json_path = self.repository.task_dir(result["task_id"]) / "task.json"
        task_data = json.loads(task_json_path.read_text(encoding="utf-8"))
        self.assertEqual(task_data["engine"], "whiteboard")

    def test_infographic_engine_persists_in_task_json(self) -> None:
        """infographic-remotion engine is written to task.json."""
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = self._cap_snapshot(True)
            code, result = self.invoke_internal_infographic("信息图持久化")
        self.assertEqual(code, EXIT_OK)
        task_json_path = self.repository.task_dir(result["task_id"]) / "task.json"
        task_data = json.loads(task_json_path.read_text(encoding="utf-8"))
        self.assertEqual(task_data["engine"], "infographic-remotion")

    # ── Pipeline engine compatibility ────────────────────────────────

    def test_pipeline_run_uses_task_engine(self) -> None:
        """Pipeline run reads engine from task — no explicit --engine needed."""
        code, result = self.invoke("task", "create", "--title", "流水线引擎", "--json")
        self.assertEqual(code, EXIT_OK)
        task = self.repository.get_task(result["task_id"])
        self.assertEqual(task.engine, Engine.WHITEBOARD)

    def test_create_options_reflects_engine_availability(self) -> None:
        """The create_options command returns engine availability info."""
        from csboard.application.commands import MountainCommands
        commands = MountainCommands(self.root, repository=FilesystemTaskRepository(self.root, project_root=self.root))
        options = commands.create_options()
        engines = {e["id"]: e for e in options["engines"]}
        self.assertIn("whiteboard", engines)
        self.assertTrue(engines["whiteboard"]["available"])
        self.assertIn("infographic-remotion", engines)

    # ── Multiple capability failure reason codes ─────────────────────

    def test_infographic_rejected_with_node_not_found_reason(self) -> None:
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = self._cap_snapshot(False, "NODE_NOT_FOUND")
            code, result = self.invoke(
                "task", "create", "--title", "Node缺失", "--engine", "infographic-remotion", "--json",
            )
        self.assertEqual(code, EXIT_VALIDATION)
        self.assertIn("NODE_NOT_FOUND", result["error"]["message"])

    def test_infographic_rejected_with_browser_not_found_reason(self) -> None:
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = self._cap_snapshot(False, "BROWSER_NOT_FOUND")
            code, result = self.invoke(
                "task", "create", "--title", "浏览器缺失", "--engine", "infographic-remotion", "--json",
            )
        self.assertEqual(code, EXIT_VALIDATION)
        self.assertIn("BROWSER_NOT_FOUND", result["error"]["message"])

    def test_infographic_rejected_with_render_script_missing_reason(self) -> None:
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = self._cap_snapshot(False, "RENDER_SCRIPT_MISSING")
            code, result = self.invoke(
                "task", "create", "--title", "脚本缺失", "--engine", "infographic-remotion", "--json",
            )
        self.assertEqual(code, EXIT_VALIDATION)
        self.assertIn("RENDER_SCRIPT_MISSING", result["error"]["message"])

    def test_infographic_rejected_with_capability_not_available_reason(self) -> None:
        with patch(_CAP_PATCH) as MockCap:
            MockCap.return_value.snapshot.return_value = self._cap_snapshot(False, "CAPABILITY_NOT_AVAILABLE")
            code, result = self.invoke(
                "task", "create", "--title", "能力不可用", "--engine", "infographic-remotion", "--json",
            )
        self.assertEqual(code, EXIT_VALIDATION)
        self.assertIn("CAPABILITY_NOT_AVAILABLE", result["error"]["message"])


if __name__ == "__main__":
    unittest.main()
