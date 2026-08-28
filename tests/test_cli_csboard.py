from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from cli.csboard import EXIT_NOT_FOUND, EXIT_OK, EXIT_VALIDATION, main


class CliCsboardTest(unittest.TestCase):
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

    def test_project_create_exposes_all_correlation_ids(self) -> None:
        code, result = self.invoke("project", "create", "--title", "CLI 标准任务", "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(result["ok"])
        self.assertEqual(result["command"], "project.create")
        self.assertTrue(all(result[key] for key in ("project_id", "run_id", "trace_id", "command_id")))

        code, shown = self.invoke("project", "show", "--project", result["project_id"], "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(shown["active_run"]["run_id"], result["run_id"])

    def test_events_and_trace_are_cross_entrypoint_queryable(self) -> None:
        _, created = self.invoke("project", "create", "--title", "可观测任务", "--json")
        code, trace = self.invoke("run", "trace", "--project", created["project_id"], "--run", created["run_id"], "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(trace["trace_id"], created["trace_id"])
        code, events = self.invoke("events", "list", "--project", created["project_id"], "--run", created["run_id"], "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(events["items"][0]["event_type"], "ProjectCreated")

    def test_not_yet_implemented_stage_is_explicitly_rejected(self) -> None:
        code, result = self.invoke("stage", "run", "--project", "project-missing", "--stage", "segment-script", "--json")
        self.assertEqual(code, EXIT_VALIDATION)
        self.assertEqual(result["error"]["code"], "CAPABILITY_NOT_AVAILABLE")

    def test_missing_project_has_stable_error(self) -> None:
        code, result = self.invoke("project", "show", "--project", "does-not-exist", "--json")
        self.assertEqual(code, EXIT_NOT_FOUND)
        self.assertEqual(result["error"]["code"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
