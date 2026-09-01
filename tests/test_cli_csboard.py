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
        code, result = self.invoke("task", "create", "--title", "CLI 标准任务", "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(result["ok"])
        self.assertEqual(result["command"], "task.create")
        self.assertTrue(all(result[key] for key in ("task_id", "run_id", "trace_id", "command_id")))

        code, shown = self.invoke("task", "show", "--task", result["task_id"], "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(shown["active_run"]["run_id"], result["run_id"])

    def test_events_and_trace_are_cross_entrypoint_queryable(self) -> None:
        _, created = self.invoke("task", "create", "--title", "可观测任务", "--json")
        code, trace = self.invoke("run", "trace", "--task", created["task_id"], "--run", created["run_id"], "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(trace["trace_id"], created["trace_id"])
        code, events = self.invoke("events", "list", "--task", created["task_id"], "--run", created["run_id"], "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(events["items"][0]["event_type"], "TaskCreated")

    def test_generate_visual_anchors_persists_av_plan_and_other_stage_is_rejected(self) -> None:
        from csboard.domain.script_preparation import prepare_script
        _, created = self.invoke("task", "create", "--title", "分割任务", "--json")
        task_id = created["task_id"]
        # Simulate input save: write script_preparation to task.json
        preparation = prepare_script("第一句话。第二句话。")
        task_json = self.root / "tasks" / task_id / "task.json"
        task_data = json.loads(task_json.read_text(encoding="utf-8"))
        task_data["script_preparation"] = preparation
        task_data["visual_anchor_enabled"] = False
        task_json.write_text(json.dumps(task_data, ensure_ascii=False, indent=2), encoding="utf-8")
        code, segmented = self.invoke("stage", "run", "--task", task_id, "--run", created["run_id"], "--stage", "generate-visual-anchors", "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertEqual(segmented["artifacts"], ["planning.av-plan"])
        # Use an unregistered stage (custom-stage is not implemented)
        code, result = self.invoke("stage", "run", "--task", task_id, "--stage", "custom-stage", "--json")
        self.assertEqual(code, EXIT_VALIDATION)
        self.assertEqual(result["error"]["code"], "CAPABILITY_NOT_AVAILABLE")

    def test_missing_project_has_stable_error(self) -> None:
        code, result = self.invoke("task", "show", "--task", "does-not-exist", "--json")
        self.assertEqual(code, EXIT_NOT_FOUND)
        self.assertEqual(result["error"]["code"], "NOT_FOUND")

    def test_artifact_show_returns_content(self) -> None:
        from csboard.domain.script_preparation import prepare_script
        _, created = self.invoke("task", "create", "--title", "Artifact 测试", "--json")
        task_id = created["task_id"]
        # Simulate input save: write script_preparation to task.json
        preparation = prepare_script("测试文案。")
        task_json = self.root / "tasks" / task_id / "task.json"
        task_data = json.loads(task_json.read_text(encoding="utf-8"))
        task_data["script_preparation"] = preparation
        task_data["visual_anchor_enabled"] = False
        task_json.write_text(json.dumps(task_data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.invoke("stage", "run", "--task", task_id, "--run", created["run_id"], "--stage", "generate-visual-anchors", "--json")
        code, result = self.invoke("artifact", "show", "--task", task_id, "--run", created["run_id"], "--key", "planning.av-plan", "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(result["ok"])
        self.assertIn("content", result)
        self.assertEqual(result["artifact_key"], "planning.av-plan")

    def test_artifact_show_missing_key(self) -> None:
        _, created = self.invoke("task", "create", "--title", "Artifact 缺失", "--json")
        code, result = self.invoke("artifact", "show", "--task", created["task_id"], "--run", created["run_id"], "--key", "nonexistent", "--json")
        self.assertEqual(code, EXIT_NOT_FOUND)

    def test_pipeline_run_gated_policy(self) -> None:
        from csboard.domain.script_preparation import prepare_script
        _, created = self.invoke("task", "create", "--title", "Pipeline 测试", "--json")
        task_id = created["task_id"]
        # Write request.json and script_preparation to task.json
        request_path = self.root / "tasks" / task_id / "request.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text('{"script": "流水线测试文案。"}', encoding="utf-8")
        preparation = prepare_script("流水线测试文案。")
        task_json = self.root / "tasks" / task_id / "task.json"
        task_data = json.loads(task_json.read_text(encoding="utf-8"))
        task_data["script_preparation"] = preparation
        task_data["visual_anchor_enabled"] = False
        task_json.write_text(json.dumps(task_data, ensure_ascii=False, indent=2), encoding="utf-8")
        code, result = self.invoke("pipeline", "run", "--task", task_id, "--policy", "gated", "--json")
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(result["ok"])
        self.assertEqual(result["policy"], "gated")
        self.assertEqual(len(result["stages_executed"]), 1)

    def test_stage_retry_missing_stage_returns_not_found(self) -> None:
        _, created = self.invoke("task", "create", "--title", "Retry 测试", "--json")
        code, result = self.invoke("stage", "retry", "--task", created["task_id"], "--run", created["run_id"], "--stage", "generate-visual-anchors", "--json")
        self.assertEqual(code, EXIT_NOT_FOUND)
        self.assertEqual(result["error"]["code"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
