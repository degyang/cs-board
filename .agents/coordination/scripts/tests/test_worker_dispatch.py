from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SOURCE = Path(__file__).parents[1]
DISPATCH = SOURCE / "dispatch_cli_agent.sh"
RUNNER = SOURCE / "run_worker_agent.sh"


class WorkerDispatchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.root = base / "project"
        self.root.mkdir()
        self.owner = base / "owner"
        self.owner.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "test"], cwd=self.root, check=True)
        subprocess.run(["git", "init", "-q", "-b", "worker"], cwd=self.owner, check=True)
        (self.root / "docs/agents/tasks").mkdir(parents=True)
        (self.root / ".agents/coordination/runtime").mkdir(parents=True)
        (self.root / "docs/agents/tasks/WORK-1.md").write_text("# WORK-1\n")
        (self.root / ".agents/coordination/agents.json").write_text(json.dumps({"agents": {"WORK": {
            "transport": "codex_exec", "thread": "", "worktree": str(self.owner),
            "model": "gpt-5.6-terra", "reasoning_effort": "medium",
        }}}))
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "contract"], cwd=self.root, check=True)
        self.commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.active = self.root / "worker.active"
        self.log = self.root / "systemd.log"
        (self.bin / "systemctl").write_text(f"#!/bin/sh\n[ -f '{self.active}' ] && exit 0\nexit 3\n")
        (self.bin / "systemd-run").write_text(f"#!/bin/sh\nprintf '%s\\n' \"$*\" > '{self.log}'\ntouch '{self.active}'\n")
        for item in self.bin.iterdir(): item.chmod(0o755)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def dispatch(self) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update({"SYSTEMCTL_BIN": str(self.bin / "systemctl"), "SYSTEMD_RUN_BIN": str(self.bin / "systemd-run")})
        return subprocess.run([
            "bash", str(DISPATCH), str(self.root), "WORK", "WORK-1",
            "docs/agents/tasks/WORK-1.md", self.commit, "返工", "2",
        ], env=env, text=True, capture_output=True)

    def test_dispatch_starts_wrapper_without_prewrite(self) -> None:
        result = self.dispatch()
        self.assertEqual(result.returncode, 0, result.stderr)
        command = self.log.read_text()
        self.assertIn("run_worker_agent.sh", command)
        self.assertIn("WORK-1", command)
        self.assertIn("返工 2", command)
        self.assertFalse((self.root / ".agents/coordination/runtime/WORK.json").exists())

    def test_dispatch_failure_does_not_publish_working(self) -> None:
        (self.bin / "systemd-run").write_text("#!/bin/sh\nexit 8\n")
        (self.bin / "systemd-run").chmod(0o755)
        result = self.dispatch()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".agents/coordination/runtime/WORK.json").exists())

    def test_worker_runner_owns_lifecycle(self) -> None:
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
        result = subprocess.run([
            "bash", str(RUNNER), str(self.root), "WORK", "WORK-1", "contract.md", "abc",
            "codex_exec", "none", str(self.owner), "gpt-5.6-terra", "medium", "初次", "1",
        ], env=env)
        self.assertEqual(result.returncode, 0)
        lines = transitions.read_text().splitlines()
        self.assertIn("--state working", lines[0])
        self.assertIn("--state review", lines[-1])


if __name__ == "__main__":
    unittest.main()
