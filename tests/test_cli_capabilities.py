from __future__ import annotations

import ast
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cli.csboard import EXIT_OK, main
from csboard.application.capabilities import CapabilityService


class CliCapabilitiesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def invoke(self, *args: str) -> tuple[int, dict]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--data-dir", str(self.root), *args])
        return code, json.loads(output.getvalue())

    def test_capabilities_command_returns_engines(self) -> None:
        code, result = self.invoke("capabilities", "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertIn("items", result)
        engines = {item["engine"] for item in result["items"]}
        self.assertIn("whiteboard", engines)
        self.assertIn("infographic-remotion", engines)

    def test_capabilities_shows_infographic_status(self) -> None:
        code, result = self.invoke("capabilities", "--json")
        self.assertEqual(code, EXIT_OK)
        infographic_item = next(
            item for item in result["items"]
            if item["engine"] == "infographic-remotion" and item["visual_source"] == "preset"
        )
        self.assertIn("supported", infographic_item)
        self.assertIn("reason_code", infographic_item)

    def test_cli_uses_the_shared_capability_read_model(self) -> None:
        expected = {"items": [{"engine": "shared-read-model"}], "providers": {"all_available": False}}
        with patch.object(CapabilityService, "snapshot", return_value=expected):
            code, result = self.invoke("capabilities", "--json")

        self.assertEqual(code, EXIT_OK)
        self.assertEqual(result, expected)

    def test_no_webapp_imports_in_capabilities(self) -> None:
        source = Path(__file__).resolve().parents[1] / "cli" / "csboard.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertFalse(
                        alias.name.startswith("webapp."),
                        f"webapp import found in CLI: {alias.name}",
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.assertFalse(
                    node.module.startswith("webapp."),
                    f"webapp import found in CLI: {node.module}",
                )


if __name__ == "__main__":
    unittest.main()
