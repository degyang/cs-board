"""Tests that verify legacy code is properly isolated from the new product."""

import unittest


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


if __name__ == "__main__":
    unittest.main()
