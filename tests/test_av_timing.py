from __future__ import annotations

import unittest

from csboard.application.av_artifacts import av_plan_document, timeline_document
from csboard.domain.av_timing import AlignmentResult, segment_script, time_voice_unit
from csboard.domain.enums import TimingSource


class AvTimingTest(unittest.TestCase):
    def test_segmenter_preserves_exact_source_ranges(self) -> None:
        source = "以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。"
        units = segment_script(source)
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].text, source)
        self.assertEqual([visual.text for visual in units[0].visual_items], ["以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。", "市场有风险，投资需谨慎。"])

    def test_whisper_boundary_switches_at_second_visual_start(self) -> None:
        unit = segment_script("以上内容基于公开数据和量化分析，仅供参考，不构成投资建议。市场有风险，投资需谨慎。")[0]
        result = time_voice_unit(unit, 10820, AlignmentResult(
            starts_ms={unit.visual_items[0].visual_id: 0, unit.visual_items[1].visual_id: 7310}, coverage=0.99, confidence=0.91,
        ))
        self.assertEqual(result.timing_source, TimingSource.WHISPER)
        self.assertEqual(result.visual_timings[1].start_ms, 7310)
        self.assertEqual(result.visual_timings[-1].end_ms, 10820)

    def test_invalid_whisper_uses_whole_unit_equal_fallback(self) -> None:
        unit = segment_script("第一句话。第二句话。第三句话。", target_sentences=3)[0]
        result = time_voice_unit(unit, 10001, AlignmentResult(
            starts_ms={item.visual_id: 0 for item in unit.visual_items}, coverage=0.99, confidence=0.91, reason_code="ALIGNMENT_NON_MONOTONIC",
        ))
        self.assertEqual(result.timing_source, TimingSource.EQUAL_FALLBACK)
        self.assertEqual([(item.start_ms, item.end_ms) for item in result.visual_timings], [(0, 3333), (3333, 6667), (6667, 10001)])
        self.assertEqual(result.alignment["reason_code"], "ALIGNMENT_NON_MONOTONIC")

    def test_artifact_documents_keep_contract_identifiers_and_local_timing(self) -> None:
        source = "第一句话。第二句话。"
        units = segment_script(source)
        plan = av_plan_document("project-1", "run-1", units, source)
        timing = time_voice_unit(units[0], 1000, None)
        timeline = timeline_document("project-1", "run-1", (timing,))
        self.assertEqual(plan["artifact_key"], "planning.av-plan")
        self.assertEqual(plan["voice_units"][0]["visual_items"][1]["source_range"]["start"], len("第一句话。"))
        self.assertEqual(timeline["units"][0]["timing_source"], "equal_fallback")
        self.assertEqual(timeline["units"][0]["visual_timings"][-1]["end_ms"], 1000)


if __name__ == "__main__":
    unittest.main()
