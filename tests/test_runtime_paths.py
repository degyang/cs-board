from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from csboard.runtime.paths import RuntimePaths


class RuntimePathsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_from_root_resolves_all_subdirs(self) -> None:
        paths = RuntimePaths.from_root(self.root)
        self.assertEqual(paths.root, self.root.resolve())
        self.assertEqual(paths.state_dir, self.root.resolve() / ".webapp")
        self.assertEqual(paths.jobs_dir, self.root.resolve() / ".webapp" / "jobs")
        self.assertEqual(paths.config_path, self.root.resolve() / ".webapp" / "config.json")
        self.assertEqual(paths.projects_dir, self.root.resolve() / ".webapp" / "projects")
        self.assertEqual(paths.temp_dir, self.root.resolve() / ".webapp" / "tmp")

    def test_from_root_resolves_relative(self) -> None:
        # from_root should resolve to absolute even with a relative path
        paths = RuntimePaths.from_root(self.root)
        self.assertTrue(paths.root.is_absolute())
        self.assertTrue(paths.state_dir.is_absolute())

    def test_ensure_dirs_creates_all(self) -> None:
        paths = RuntimePaths.from_root(self.root)
        self.assertFalse(paths.state_dir.exists())
        paths.ensure_dirs()
        self.assertTrue(paths.state_dir.is_dir())
        self.assertTrue(paths.jobs_dir.is_dir())
        self.assertTrue(paths.projects_dir.is_dir())
        self.assertTrue(paths.temp_dir.is_dir())

    def test_ensure_dirs_idempotent(self) -> None:
        paths = RuntimePaths.from_root(self.root)
        paths.ensure_dirs()
        paths.ensure_dirs()  # should not raise
        self.assertTrue(paths.state_dir.is_dir())

    def test_frozen(self) -> None:
        paths = RuntimePaths.from_root(self.root)
        with self.assertRaises(AttributeError):
            paths.root = Path("/other")  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
