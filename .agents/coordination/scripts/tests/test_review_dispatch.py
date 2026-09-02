from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "dispatch_review_agent.sh"
RUNNER = Path(__file__).parents[1] / "run_review_agent.sh"


class ReviewDispatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "docs/agents/tasks").mkdir(parents=True)
        (self.root / ".agents/coordination/runtime").mkdir(parents=True)
        self.owner = self.root / "owner"
        self.owner.mkdir()
        (self.root / "docs/agents/tasks/CORE-1.md").write_text("# CORE-1\n")
        (self.root / "docs/agents/status.md").write_text(
            "| Task | Owner | Status | Contract | Delivery | Review |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| `CORE-1` | CORE | REVIEW_READY | `docs/agents/tasks/CORE-1.md` | `abc1234` | pending |\n"
        )
        (self.root / ".agents/coordination/agents.json").write_text(
            json.dumps({"agents": {"CORE": {"worktree": str(self.owner)}, "REVIEWER": {"transport": "codex_exec"}}})
        )
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.log = self.root / "systemd-run.log"
        self.active = self.root / "reviewer.active"
        (self.bin / "systemctl").write_text(
            f"#!/bin/sh\n[ -f '{self.active}' ] && exit 0\nexit 3\n"
        )
        (self.bin / "systemd-run").write_text(
            f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{self.log}'\ntouch '{self.active}'\nexit 0\n"
        )
        for item in self.bin.iterdir():
            item.chmod(0o755)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_dispatch(self) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update({"SYSTEMCTL_BIN": str(self.bin / "systemctl"), "SYSTEMD_RUN_BIN": str(self.bin / "systemd-run")})
        return subprocess.run(["bash", str(SCRIPT), str(self.root)], env=env, text=True, capture_output=True)

    def test_starts_first_review_without_publishing_runtime(self) -> None:
        result = self.run_dispatch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CORE-1", self.log.read_text())
        self.assertFalse((self.root / ".agents/coordination/runtime/REVIEWER.json").exists())

    def test_completed_review_waits_for_pm_consumption(self) -> None:
        (self.root / ".agents/coordination/runtime/REVIEWER.json").write_text(
            json.dumps({"state": "review", "task_id": "CORE-1"})
        )
        result = self.run_dispatch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.log.exists())

    def test_start_failure_does_not_publish_working(self) -> None:
        (self.bin / "systemd-run").write_text("#!/bin/sh\nexit 7\n")
        (self.bin / "systemd-run").chmod(0o755)
        result = self.run_dispatch()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".agents/coordination/runtime/REVIEWER.json").exists())

    def test_supervised_runner_publishes_working_then_review(self) -> None:
        dashboard = self.root / "dashboard"
        dashboard.mkdir()
        transitions = self.root / "transitions.log"
        teamctl = dashboard / "teamctl.mjs"
        teamctl.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{transitions}'\n")
        teamctl.chmod(0o755)
        node = self.root / "node"
        node.write_text("#!/bin/sh\nexec \"$@\"\n")
        node.chmod(0o755)
        codex = self.root / "codex"
        codex.write_text("#!/bin/sh\nexit 0\n")
        codex.chmod(0o755)
        env = os.environ.copy()
        env.update({"TEAM_DASHBOARD_DIR": str(dashboard), "NODE_BIN": str(node), "CODEX_BIN": str(codex)})
        result = subprocess.run(
            ["bash", str(RUNNER), str(self.root), "CORE-1", "contract.md", "abc", str(self.owner)],
            env=env,
        )
        self.assertEqual(result.returncode, 0)
        lines = transitions.read_text().splitlines()
        self.assertIn("--state working", lines[0])
        self.assertIn("--state review", lines[-1])

    def test_supervised_runner_marks_failed_process_blocked(self) -> None:
        dashboard = self.root / "dashboard"
        dashboard.mkdir()
        transitions = self.root / "transitions.log"
        teamctl = dashboard / "teamctl.mjs"
        teamctl.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{transitions}'\n")
        teamctl.chmod(0o755)
        node = self.root / "node"
        node.write_text("#!/bin/sh\nexec \"$@\"\n")
        node.chmod(0o755)
        codex = self.root / "codex"
        codex.write_text("#!/bin/sh\nexit 11\n")
        codex.chmod(0o755)
        env = os.environ.copy()
        env.update({"TEAM_DASHBOARD_DIR": str(dashboard), "NODE_BIN": str(node), "CODEX_BIN": str(codex)})
        result = subprocess.run(
            ["bash", str(RUNNER), str(self.root), "CORE-1", "contract.md", "abc", str(self.owner)],
            env=env,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--state blocked", transitions.read_text().splitlines()[-1])


if __name__ == "__main__":
    unittest.main()
