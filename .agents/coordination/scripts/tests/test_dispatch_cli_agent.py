from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SOURCE = Path(__file__).parents[1] / "dispatch_cli_agent.sh"


class DispatchCliAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "test@example.test"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Test"], check=True)
        (self.root / ".agents/coordination").mkdir(parents=True)
        (self.root / "docs/agents/tasks").mkdir(parents=True)
        (self.root / "docs/agents/tasks/WEB-1.md").write_text("# WEB-1\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "contract"], check=True)
        self.commit = subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True).strip()
        (self.root / ".agents/coordination/agents.json").write_text(
            json.dumps(
                {
                    "agents": {
                        "WEB": {
                            "transport": "codex_cli",
                            "thread": "worker-uuid",
                            "worktree": str(self.root),
                            "model": "test-model",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        self.bin = self.root / "fake-bin"
        self.bin.mkdir()
        self.calls = self.root / "calls"
        self.active = self.root / "worker-active"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def executable(self, name: str, body: str) -> Path:
        target = self.bin / name
        target.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        target.chmod(0o755)
        return target

    def environment(self, *, active: bool = False) -> dict[str, str]:
        if active:
            self.active.touch()
            runtime = self.root / ".agents/coordination/runtime"
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / "WEB.json").write_text(json.dumps({"task_id": "WEB-1"}))
        systemctl = self.executable("systemctl", f"[ -f '{self.active}' ]")
        systemd_run = self.executable(
            "systemd-run",
            f"printf '%s\\n' \"$*\" >> '{self.calls}'\ntouch '{self.active}'",
        )
        npm = self.executable("npm", f"printf 'npm %s\\n' \"$*\" >> '{self.calls}'")
        codex = self.executable("codex", "exit 0")
        environment = os.environ.copy()
        environment.update(
            SYSTEMCTL_BIN=str(systemctl),
            SYSTEMD_RUN_BIN=str(systemd_run),
            NPM_BIN=str(npm),
            CODEX_BIN=str(codex),
            TEAM_DASHBOARD_DIR=str(self.root),
        )
        return environment

    def run_dispatch(self, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "bash",
                str(SOURCE),
                str(self.root),
                "WEB",
                "WEB-1",
                "docs/agents/tasks/WEB-1.md",
                self.commit,
            ],
            text=True,
            capture_output=True,
            env=environment,
        )

    def test_starts_worker_in_independent_systemd_unit_and_returns(self) -> None:
        result = self.run_dispatch(self.environment())
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls.read_text(encoding="utf-8")
        self.assertIn("--unit=cs-board-agent-web.service", calls)
        self.assertIn("run_worker_agent.sh", calls)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", calls)
        state = json.loads((self.root / ".agents/coordination/runtime/dispatch-WEB.json").read_text())
        self.assertEqual(state["state"], "started")

    def test_does_not_overlap_an_active_worker_unit(self) -> None:
        result = self.run_dispatch(self.environment(active=True))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.calls.exists())
        state = json.loads((self.root / ".agents/coordination/runtime/dispatch-WEB.json").read_text())
        self.assertEqual(state["state"], "already-running")


if __name__ == "__main__":
    unittest.main()
