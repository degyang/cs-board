from __future__ import annotations

import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from csboard.runtime.process_supervisor import ProcessSupervisor


class ProcessSupervisorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.supervisor = ProcessSupervisor()

    def tearDown(self) -> None:
        self.supervisor.cancel_all()
        self.temporary.cleanup()

    def test_start_returns_handle(self) -> None:
        handle = self.supervisor.start(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            cwd=self.root,
        )
        self.assertEqual(len(handle.process_id), 12)
        self.assertIsNone(handle.popen.poll())
        self.assertIn(handle, self.supervisor.active_handles())

    def test_terminate_stops_process(self) -> None:
        handle = self.supervisor.start(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            cwd=self.root,
        )
        self.supervisor.terminate(handle)
        self.assertNotEqual(handle.popen.poll(), None)
        self.assertNotIn(handle, self.supervisor.active_handles())

    def test_cancel_all_stops_everything(self) -> None:
        for _ in range(3):
            self.supervisor.start(
                [sys.executable, "-c", "import time; time.sleep(30)"],
                cwd=self.root,
            )
        self.assertEqual(len(self.supervisor.active_handles()), 3)
        stopped = self.supervisor.cancel_all()
        self.assertEqual(stopped, 3)
        self.assertEqual(len(self.supervisor.active_handles()), 0)

    def test_cleanup_finished_removes_exited(self) -> None:
        handle = self.supervisor.start(
            [sys.executable, "-c", "pass"],
            cwd=self.root,
        )
        handle.popen.wait()
        removed = self.supervisor.cleanup_finished()
        self.assertEqual(removed, 1)
        self.assertEqual(len(self.supervisor.active_handles()), 0)

    def test_stdout_redirected_to_file(self) -> None:
        out = self.root / "output.log"
        handle = self.supervisor.start(
            [sys.executable, "-c", "print('hello')"],
            cwd=self.root,
            stdout=out,
        )
        handle.popen.wait()
        self.assertEqual(out.read_text().strip(), "hello")

    def test_terminate_already_exited_is_noop(self) -> None:
        handle = self.supervisor.start(
            [sys.executable, "-c", "pass"],
            cwd=self.root,
        )
        handle.popen.wait()
        self.supervisor.terminate(handle)  # should not raise


if __name__ == "__main__":
    unittest.main()
