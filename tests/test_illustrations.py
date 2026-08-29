from __future__ import annotations

import unittest
from pathlib import Path

from csboard.application.illustrations import illustration_manifest_document
from tests.test_mountain_contracts import validator_for


class IllustrationTest(unittest.TestCase):
    def test_manifest_separates_source_and_final_and_validates(self) -> None:
        document = illustration_manifest_document("project-1", "run-1", [{"visual_id": "visual-001-01", "source_image_path": "images/source.png", "final_image_path": "images/final.png", "payload": b"image"}], "default", "fake")
        self.assertNotEqual(document["illustrations"][0]["source_image_path"], document["illustrations"][0]["final_image_path"])
        schema = Path(__file__).resolve().parents[1] / "schemas" / "mountain" / "illustration-manifest.schema.json"
        self.assertEqual([], list(validator_for(schema).iter_errors(document)))
