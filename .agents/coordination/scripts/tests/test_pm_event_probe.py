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

    def test_max_actions_bounds_pm_cycle_to_one_fact_transition(self) -> None:
        self.write_status([
            "| `CORE-1` | CORE | REVIEW_READY | pending | abc | pending |",
            "| `MEDIA-1` | MEDIA | REVIEW_READY | pending | def | pending |",
        ])
        result = subprocess.run([
            "python3", str(SOURCE / "pm_event_probe.py"), "probe", "--project", str(self.root),
            "--now", "2026-09-02T04:05:00Z", "--max-actions", "1",
        ], check=True, capture_output=True, text=True)
        self.assertEqual(len(json.loads(result.stdout)["actions"]), 1)

    def test_completed_agent_is_retained_until_idle_timeout(self) -> None:
        self.write_status(["| `DONE-1` | DONE | APPROVED | pending | abc | accepted |"])
        (self.root / ".agents/coordination/agents.json").write_text(json.dumps({"agents": {
            "PM": {"transport": "codex_cli", "thread": "pm"},
            "REVIEWER": {"transport": "codex_exec"},
            "DONE": {"transport": "codex_exec"},
        }}))
        (self.root / ".agents/coordination/policy.json").write_text(json.dumps({
            "max_registered_agents": 5, "idle_retention_seconds": 600,
            "protected_roles": ["PM", "REVIEWER"],
        }))
        self.write_runtime("DONE", state="idle", task_id="DONE-1", heartbeat_at="2026-09-02T03:55:01Z")
        self.assertEqual(self.probe(), "")
        self.write_runtime("DONE", state="idle", task_id="DONE-1", heartbeat_at="2026-09-02T03:49:59Z")
        action = json.loads(self.probe())["actions"][0]
        self.assertEqual(action["kind"], "retire-agent")
        self.assertEqual(action["reason"], "retention-expired")

    def test_capacity_pressure_prioritizes_oldest_timed_out_agent(self) -> None:
        self.write_status([
            "| `DONE-A` | A | APPROVED | pending | a | accepted |",
            "| `DONE-B` | B | APPROVED | pending | b | accepted |",
            "| `WEB-1` | WEB | READY | pending | pending | pending |",
        ])
        agents = {name: {"transport": "codex_exec"} for name in ("A", "B", "WEB", "X")}
        agents.update({"PM": {"transport": "codex_cli"}, "REVIEWER": {"transport": "codex_exec"}})
        (self.root / ".agents/coordination/agents.json").write_text(json.dumps({"agents": agents}))
        (self.root / ".agents/coordination/policy.json").write_text(json.dumps({
            "max_registered_agents": 5, "idle_retention_seconds": 600,
            "protected_roles": ["PM", "REVIEWER"],
        }))
        self.write_runtime("A", state="idle", task_id="DONE-A", heartbeat_at="2026-09-02T03:40:00Z")
        self.write_runtime("B", state="idle", task_id="DONE-B", heartbeat_at="2026-09-02T03:45:00Z")
        actions = json.loads(self.probe())["actions"]
        self.assertEqual(actions[0]["kind"], "retire-agent")
        self.assertEqual(actions[0]["owner"], "A")
        self.assertEqual(actions[0]["reason"], "capacity-pressure")

    def test_protected_roles_are_never_retired(self) -> None:
        self.write_status(["| `PM-DONE` | PM | APPROVED | pending | abc | accepted |"])
        (self.root / ".agents/coordination/policy.json").write_text(json.dumps({
            "idle_retention_seconds": 60, "protected_roles": ["PM", "REVIEWER"],
        }))
        self.write_runtime("PM", state="idle", task_id="PM-DONE", heartbeat_at="2026-09-02T01:00:00Z")
        self.assertEqual(self.probe(), "")

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

    def test_coordinator_task_never_starves_worker_review(self) -> None:
        self.write_status(
            [
                "| `CEO-RECOVERY-1` | PM | IN_PROGRESS | pending | pending | pending |",
                "| `WEB-1` | WEB | REVIEW_READY | pending | abc | pending |",
            ]
        )
        self.write_runtime("PM", task_id="CEO-RECOVERY-1", heartbeat_at="2026-09-02T03:00:00Z")
        actions = json.loads(self.probe())["actions"]
        self.assertEqual(
            actions,
            [
                {
                    "kind": "review",
                    "review_digest": None,
                    "task_id": "WEB-1",
                    "owner": "WEB",
                    "status": "REVIEW_READY",
                }
            ],
        )

    def test_worker_review_runtime_requests_tracked_review_ready(self) -> None:
        for status in ("DISPATCHED", "IN_PROGRESS"):
            with self.subTest(status=status):
                self.write_status([f"| `WEB-1` | WEB | {status} | pending | abc | pending |"])
                self.write_runtime("WEB", state="review", task_id="WEB-1")
                actions = json.loads(self.probe())["actions"]
                self.assertEqual(
                    actions,
                    [{"kind": "record-review-ready", "task_id": "WEB-1", "owner": "WEB", "status": status}],
                )

    def test_missing_runtime_emits_recovery(self) -> None:
        self.write_status(["| `CORE-1` | CORE | IN_PROGRESS | pending | pending | pending |"])
        action = json.loads(self.probe())["actions"][0]
        self.assertEqual(action["kind"], "recover-stale")
        self.assertEqual(action["reason"], "runtime_missing")

    def test_idle_and_blocked_in_progress_emit_recovery(self) -> None:
        for status in ("DISPATCHED", "IN_PROGRESS"):
            for state in ("idle", "blocked"):
                with self.subTest(status=status, state=state):
                    self.write_status([f"| `CORE-1` | CORE | {status} | pending | pending | pending |"])
                    self.write_runtime("CORE", state=state)
                    action = json.loads(self.probe())["actions"][0]
                    self.assertEqual(action["reason"], f"runtime_{state}")

    def test_ready_is_suppressed_while_same_owner_has_active_task(self) -> None:
        for status in ("DISPATCHED", "IN_PROGRESS", "REVIEW_READY", "CHANGES_REQUESTED", "BLOCKED"):
            with self.subTest(status=status):
                self.write_status(
                    [
                        f"| `WEB-1` | WEB | {status} | pending | pending | pending |",
                        "| `WEB-2` | WEB | READY | pending | pending | pending |",
                    ]
                )
                if status == "IN_PROGRESS":
                    self.write_runtime("WEB", task_id="WEB-1")
                output = self.probe()
                actions = json.loads(output)["actions"] if output else []
                self.assertFalse(
                    any(action["kind"] == "dispatch" and action["task_id"] == "WEB-2" for action in actions)
                )

    def test_changes_requested_redispatches_same_task_before_later_ready_work(self) -> None:
        self.write_status(
            [
                "| `WEB-1` | WEB | CHANGES_REQUESTED | pending | abc | requested |",
                "| `WEB-2` | WEB | READY | pending | pending | pending |",
            ]
        )
        actions = json.loads(self.probe())["actions"]
        self.assertEqual(
            actions,
            [{"kind": "dispatch", "task_id": "WEB-1", "owner": "WEB", "status": "CHANGES_REQUESTED"}],
        )

    def test_changes_requested_waits_when_owner_has_another_active_task(self) -> None:
        self.write_status(
            [
                "| `WEB-1` | WEB | CHANGES_REQUESTED | pending | abc | requested |",
                "| `WEB-0` | WEB | IN_PROGRESS | pending | abc | pending |",
            ]
        )
        self.write_runtime("WEB", task_id="WEB-0")
        output = self.probe()
        actions = json.loads(output)["actions"] if output else []
        self.assertFalse(any(action["kind"] == "dispatch" for action in actions))

    def test_review_event_is_emitted_once_after_ack(self) -> None:
        self.write_status(["| `CORE-1` | CORE | REVIEW_READY | pending | abc | pending |"])
        event = json.loads(self.probe())
        self.assertEqual(event["actions"][0]["kind"], "review")
        subprocess.run(
            ["python3", str(SOURCE / "pm_event_probe.py"), "ack", "--project", str(self.root), "--signature", event["signature"]],
            check=True,
        )
        self.assertEqual(self.probe(), "")

    def test_supervised_review_requires_completion_bound_to_delivery(self) -> None:
        self.write_status(["| `CORE-1` | CORE | REVIEW_READY | pending | abc | pending |"])
        (self.root / ".agents/coordination/agents.json").write_text(json.dumps({"agents": {
            "PM": {"transport": "codex_cli", "thread": "pm"},
            "REVIEWER": {"transport": "codex_exec"},
        }}))
        self.assertEqual(self.probe(), "")
        runtime = self.root / ".agents/coordination/runtime"
        (runtime / "review-completed.json").write_text(json.dumps({
            "state": "completed", "task_id": "CORE-1", "delivery": "old",
        }))
        self.assertEqual(self.probe(), "")
        (runtime / "review-completed.json").write_text(json.dumps({
            "state": "completed", "task_id": "CORE-1", "delivery": "abc",
        }))
        event = json.loads(self.probe())
        self.assertEqual(event["actions"][0]["task_id"], "CORE-1")

    def test_new_or_revised_review_reopens_acknowledged_event(self) -> None:
        self.write_status(["| `CORE-1` | CORE | REVIEW_READY | pending | abc | pending |"])
        first = json.loads(self.probe())
        subprocess.run(
            ["python3", str(SOURCE / "pm_event_probe.py"), "ack", "--project", str(self.root), "--signature", first["signature"]],
            check=True,
        )
        reviews = self.root / "docs/agents/reviews"
        reviews.mkdir(parents=True)
        (reviews / "CORE-1.md").write_text("Verdict: `CHANGES_REQUESTED`\n", encoding="utf-8")
        second = json.loads(self.probe())
        self.assertNotEqual(second["signature"], first["signature"])
        first_digest = second["actions"][0]["review_digest"]
        (reviews / "CORE-1.md").write_text("Verdict: `APPROVED`\n", encoding="utf-8")
        third = json.loads(self.probe())
        self.assertNotEqual(third["actions"][0]["review_digest"], first_digest)

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
        environment["CODEX_BIN"] = str(fake_codex)
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
        environment["CODEX_BIN"] = str(fake_codex)
        result = subprocess.run(
            ["bash", str(SOURCE / "run_pm_if_needed.sh"), str(self.root)],
            env=environment,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(self.probe())["actions"][0]["kind"], "review")

    def test_wrapper_success_does_not_ack_unchanged_event(self) -> None:
        self.write_status(["| `CORE-1` | CORE | REVIEW_READY | pending | abc | pending |"])
        (self.root / ".agents/coordination/agents.json").write_text(
            json.dumps({"agents": {"PM": {"transport": "codex_cli", "thread": "real-looking-uuid"}}}),
            encoding="utf-8",
        )
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        fake_codex = fake_bin / "codex"
        fake_codex.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        fake_codex.chmod(0o755)
        environment = os.environ.copy()
        environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
        environment["CODEX_BIN"] = str(fake_codex)
        result = subprocess.run(["bash", str(SOURCE / "run_pm_if_needed.sh"), str(self.root)], env=environment)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(json.loads(self.probe())["actions"][0]["task_id"], "CORE-1")


if __name__ == "__main__":
    unittest.main()
