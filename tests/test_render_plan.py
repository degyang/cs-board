from __future__ import annotations

import unittest
from pathlib import Path
from csboard.application.render_plan import render_manifest_document
from tests.test_mountain_contracts import validator_for

class RenderPlanTest(unittest.TestCase):
 def test_uses_timeline_duration(self):
  timeline={"units":[{"visual_timings":[{"visual_id":"visual-001-01","start_ms":0,"end_ms":900}]}]}
  illustrations={"illustrations":[{"visual_id":"visual-001-01"}]}
  document=render_manifest_document("project-1","run-1",timeline,illustrations)
  self.assertEqual(document["clips"][0]["duration_ms"],900)
  schema=Path(__file__).resolve().parents[1]/"schemas"/"mountain"/"render-manifest.schema.json"
  self.assertEqual([],list(validator_for(schema).iter_errors(document)))
