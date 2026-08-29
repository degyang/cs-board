from __future__ import annotations
import unittest
from csboard.application.composition import final_manifest_document, require_valid_final

class CompositionTest(unittest.TestCase):
 def test_invalid_av_cannot_be_accepted(self):
  timeline={"units":[{"duration_ms":1000}]}; render={"clips":[{"duration_ms":1000}]}
  good=final_manifest_document("project-1","run-1",timeline,render,1000)
  self.assertTrue(require_valid_final(good)["validation"]["passed"])
  bad=final_manifest_document("project-1","run-1",timeline,render,1300)
  with self.assertRaisesRegex(ValueError,"禁止报告") : require_valid_final(bad)
