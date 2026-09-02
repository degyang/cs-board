from __future__ import annotations

import json
import os
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

    def write_runtime(
        self,
        owner: str,
        *,
        state: str = "working",
        task_id: str = "CORE-1",
        heartbeat_at: str = "2026-09-02T04:00:00Z",
    ) -> None:
        runtime = self.root / ".agents/coordination/runtime"
        runtime.mkdir(parents=True, exist_ok=True)
        (runtime / f"{owner}.json").write_text(
            json.dumps(
                {
                    "role": owner,
                    "state": state,
                    "task_id": task_id,
                    "heartbeat_at": heartbeat_at,
                }
            ),
            encoding="utf-8",
        )

    def probe(self) -> str:
        result = subprocess.run(
            [
                "python3",
                str(SOURCE / "pm_event_probe.py"),
                "probe",
                "--project",
                str(self.root),
                "--now",
                "2026-09-02T04:05:00Z",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def test_no_actionable_event_has_no_output(self) -> None:
        self.write_status(["| `CORE-1` | CORE | IN_PROGRESS | pending | pending | pending |"])
        self.write_runtime("CORE")
        self.assertEqual(self.probe(), "")

    def test_expired_in_progress_emits_recovery_before_other_actions(self) -> None:
        self.write_status(
            [
                "| `CORE-1` | CORE | IN_PROGRESS | pending | pending | pending |",
                "| `WEB-1` | WEB | READY | pending | pending | pending |",
            ]
        )
        self.write_runtime("CORE", heartbeat_at="2026-09-02T03:00:00Z")
        actions = json.loads(self.probe())["actions"]
        self.assertEqual(actions[0]["kind"], "recover-stale")
        self.assertEqual(actions[0]["reason"], "heartbeat_expired")
        self.assertEqual(actions[1]["kind"], "dispatch")

    def test_missing_runtime_emits_recovery(self) -> None:
        self.write_status(["| `CORE-1` | CORE | IN_PROGRESS | pending | pending | pending |"])
        action = json.loads(self.probe())["actions"][0]
        self.assertEqual(action["kind"], "recover-stale")
        self.assertEqual(action["reason"], "runtime_missing")

    def test_idle_and_blocked_in_progress_emit_recovery(self) -> None:
        for state in ("idle", "blocked"):
            with self.subTest(state=state):
                self.write_status(["| `CORE-1` | CORE | IN_PROGRESS | pending | pending | pending |"])
                self.write_runtime("CORE", state=state)
                action = json.loads(self.probe())["actions"][0]
                self.assertEqual(action["reason"], f"runtime_{state}")

    def test_ready_is_suppressed_while_same_owner_has_active_task(self) -> None:
        self.write_status(
            [
                "| `WEB-1` | WEB | IN_PROGRESS | pending | pending | pending |",
                "| `WEB-2` | WEB | READY | pending | pending | pending |",
            ]
        )
        self.write_runtime("WEB", task_id="WEB-1")
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

    def test_wrapper_does_not_call_model_when_there_is_no_event(self) -> None:
        self.write_status(["| `CORE-1` | CORE | APPROVED | pending | abc | accepted |"])
        (self.root / ".agents/coordination/agents.json").write_text(
            json.dumps({"agents": {"PM": {"transport": "codex_cli", "thread": "real-looking-uuid"}}}),
            encoding="utf-8",
        )
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        marker = self.root / "codex-called"
        fake_codex = fake_bin / "codex"
        fake_codex.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 99\n", encoding="utf-8")
        fake_codex.chmod(0o755)
        environment = os.environ.copy()
        environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
        subprocess.run(
            ["bash", str(SOURCE / "run_pm_if_needed.sh"), str(self.root)],
            check=True,
            env=environment,
        )
        self.assertFalse(marker.exists())

    def test_wrapper_failure_does_not_ack_event(self) -> None:
        self.write_status(["| `CORE-1` | CORE | REVIEW_READY | pending | abc | pending |"])
        (self.root / ".agents/coordination/agents.json").write_text(
            json.dumps({"agents": {"PM": {"transport": "codex_cli", "thread": "real-looking-uuid"}}}),
            encoding="utf-8",
        )
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        fake_codex = fake_bin / "codex"
        fake_codex.write_text("#!/bin/sh\nexit 9\n", encoding="utf-8")
        fake_codex.chmod(0o755)
        environment = os.environ.copy()
        environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
        result = subprocess.run(
            ["bash", str(SOURCE / "run_pm_if_needed.sh"), str(self.root)],
            env=environment,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(self.probe())["actions"][0]["kind"], "review")


if __name__ == "__main__":
    unittest.main()
