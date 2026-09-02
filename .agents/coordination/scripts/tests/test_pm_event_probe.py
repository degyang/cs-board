from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SOURCE = Path(__file__).parents[1]


class PMEventProbeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "docs/agents/tasks").mkdir(parents=True)
        (self.root / ".agents/coordination/scripts").mkdir(parents=True)
        (self.root / ".agents/coordination/agents.json").write_text(
            json.dumps({"agents": {"PM": {"transport": "orchestrator", "thread": "/root/pm"}}}),
            encoding="utf-8",
        )
        for name in ("pm_event_probe.py", "run_pm_if_needed.sh"):
            (self.root / ".agents/coordination/scripts" / name).write_bytes((SOURCE / name).read_bytes())

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_status(self, rows: list[str]) -> None:
        table = [
            "| Task | Owner | Status | Contract | Delivery | Review |",
            "| --- | --- | --- | --- | --- | --- |",
            *rows,
        ]
        (self.root / "docs/agents/status.md").write_text("\n".join(table) + "\n", encoding="utf-8")

    def probe(self) -> str:
        result = subprocess.run(
            ["python3", str(SOURCE / "pm_event_probe.py"), "probe", "--project", str(self.root)],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def test_no_actionable_event_has_no_output(self) -> None:
        self.write_status(["| `CORE-1` | CORE | IN_PROGRESS | pending | pending | pending |"])
        self.assertEqual(self.probe(), "")

    def test_review_event_is_emitted_once_after_ack(self) -> None:
        self.write_status(["| `CORE-1` | CORE | REVIEW_READY | pending | abc | pending |"])
        event = json.loads(self.probe())
        self.assertEqual(event["actions"][0]["kind"], "review")
        subprocess.run(
            ["python3", str(SOURCE / "pm_event_probe.py"), "ack", "--project", str(self.root), "--signature", event["signature"]],
            check=True,
        )
        self.assertEqual(self.probe(), "")

    def test_satisfied_backlog_dependency_requests_promotion(self) -> None:
        self.write_status(
            [
                "| `CORE-1` | CORE | APPROVED | pending | abc | accepted |",
                "| `WEB-2` | WEB | BACKLOG | `docs/agents/tasks/WEB-2.md` | pending | blocked |",
            ]
        )
        (self.root / "docs/agents/tasks/WEB-2.md").write_text(
            "# WEB-2\n\n- Depends on: `CORE-1=APPROVED`\n",
            encoding="utf-8",
        )
        event = json.loads(self.probe())
        self.assertEqual(event["actions"][0]["kind"], "promote-ready")

    def test_wrapper_does_not_call_model_without_cli_registration(self) -> None:
        self.write_status(["| `CORE-1` | CORE | REVIEW_READY | pending | abc | pending |"])
        subprocess.run(["bash", str(SOURCE / "run_pm_if_needed.sh"), str(self.root)], check=True)
        state = json.loads((self.root / ".agents/coordination/runtime/pm-scheduler.json").read_text(encoding="utf-8"))
        self.assertEqual(state["state"], "not-configured")


if __name__ == "__main__":
    unittest.main()
