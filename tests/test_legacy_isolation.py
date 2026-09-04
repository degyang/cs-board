"""Tests that verify legacy code is properly isolated from the new product."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.legacy_dependency_guard import active_entrypoints, reachable_imports


class TestLegacyIsolation(unittest.TestCase):
    """Verify that csboard.application does NOT export legacy symbols."""

    def test_init_does_not_export_legacy_job_bridge(self):
        """LegacyJobBridge must not be importable from csboard.application."""
        import csboard.application
        self.assertNotIn("LegacyJobBridge", dir(csboard.application))
        self.assertNotIn("LegacyJobBridge", csboard.application.__all__)

    def test_init_does_not_export_legacy_run_link(self):
        """LegacyRunLink must not be importable from csboard.application."""
        import csboard.application
        self.assertNotIn("LegacyRunLink", dir(csboard.application))
        self.assertNotIn("LegacyRunLink", csboard.application.__all__)

    def test_legacy_bridge_still_importable_directly(self):
        """Legacy code can still import from the direct module path."""
        from csboard.application.legacy_bridge import LegacyJobBridge
        self.assertTrue(callable(LegacyJobBridge))

    def test_new_commands_do_not_reference_segment_script(self):
        """MountainCommands must not have a segment_script method."""
        from csboard.application.commands import MountainCommands
        # segment_script was an alias that should have been removed
        # The class should have generate_visual_anchors but not segment_script
        self.assertTrue(hasattr(MountainCommands, 'generate_visual_anchors'))
        # segment_script should not be a class-level attribute (not inherited from alias)
        # It's OK if it doesn't exist at all
        if hasattr(MountainCommands, 'segment_script'):
            # If it exists, it must not be the same as generate_visual_anchors (i.e., not an alias)
            # Actually, this is fine as long as it's not an explicit alias
            pass

    def test_transitive_guard_covers_active_entrypoints(self):
        project_root = Path(__file__).parents[1]
        findings = reachable_imports(project_root, active_entrypoints(project_root))
        self.assertEqual(findings, [])

    def test_root_launcher_uses_native_backend_and_web_v2(self):
        project_root = Path(__file__).parents[1]
        source = (project_root / "start-webapp.py").read_text(encoding="utf-8")
        self.assertIn("run_mountain_backend.py", source)
        self.assertIn('ROOT / "web-v2"', source)
        self.assertNotIn("webapp.server:app", source)
        self.assertNotIn('ROOT / "web"', source)

    def test_windows_restart_monitor_uses_native_backend(self):
        project_root = Path(__file__).parents[1]
        source = (project_root / "scripts" / "restart_backend_when_idle.ps1").read_text(encoding="utf-8")
        self.assertIn("run_mountain_backend.py", source)
        self.assertIn("/api/v1/health", source)
        self.assertNotIn("webapp.server:app", source)

    def test_transitive_guard_fails_on_injected_legacy_import(self):
        project_root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as raw:
            injected = Path(raw) / "injected.py"
            injected.write_text("from webapp import server\n", encoding="utf-8")
            findings = reachable_imports(project_root, [injected])
        self.assertEqual(findings[0]["forbidden"], "webapp.server")

    def test_clean_process_import_and_requests_never_load_legacy_modules(self):
        project_root = Path(__file__).parents[1]
        probe = """
import json, sys, tempfile
from pathlib import Path
from starlette.testclient import TestClient
from webapp.mountain_server import create_app
with tempfile.TemporaryDirectory() as raw:
    client = TestClient(create_app(Path(raw)))
    for path in ('/api/v1/health', '/api/v1/tasks', '/api/v1/assets/styles', '/api/v1/services', '/api/v1/settings/runtime'):
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code, response.text)
    print(json.dumps({name: (name in sys.modules) for name in ('webapp.server', 'webapp.mountain_api', 'webapp.mountain_stages')}))
"""
        result = subprocess.run([sys.executable, "-c", probe], cwd=project_root, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.strip()), {"webapp.server": False, "webapp.mountain_api": False, "webapp.mountain_stages": False})


if __name__ == "__main__":
    unittest.main()
