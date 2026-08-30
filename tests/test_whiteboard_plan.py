from __future__ import annotations

import unittest

from csboard.application.whiteboard_plan import storyboard_document, storyboard_ids
from csboard.domain.av_timing import segment_script
from tests.test_mountain_contracts import validator_for
from pathlib import Path


class WhiteboardPlanTest(unittest.TestCase):
    def test_storyboard_preserves_every_visual_item_and_validates(self) -> None:
        units = segment_script("第一句话。第二句话。第三句话。", target_sentences=2)
        document = storyboard_document("task-1", "run-1", units)
        expected = {item.visual_id for unit in units for item in unit.visual_items}
        self.assertEqual(storyboard_ids(document), expected)
        schema = Path(__file__).resolve().parents[1] / "schemas" / "mountain" / "storyboard.schema.json"
        self.assertEqual([], list(validator_for(schema).iter_errors(document)))


if __name__ == "__main__":
    unittest.main()
