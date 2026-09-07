"""P0 regression coverage for Voice Unit-scoped subtitle timing."""

from __future__ import annotations

from pathlib import Path

from csboard.application.composition import CompositionService
from csboard.domain.av_timing import AlignmentResult, segment_script, time_voice_unit
from csboard.domain.enums import TimingSource


def _char_alignment(text: str, *, coverage: float = 1.0, confidence: float = 0.9) -> AlignmentResult:
    return AlignmentResult(
        starts_ms={f"char:{index}": index * 100 for index in range(len(text))},
        coverage=coverage,
        confidence=confidence,
    )


def test_whisper_subtitle_cues_are_local_monotonic_and_lossless():
    unit = segment_script("第一句话，第二句话。第三句话！", target_sentences=3)[0]
    timing = time_voice_unit(unit, 3000, _char_alignment(unit.text))

    assert timing.subtitle_timing_source is TimingSource.WHISPER
    assert "".join(cue.text for cue in timing.subtitle_cues) == unit.text
    assert timing.subtitle_cues[0].start_ms == 0
    assert timing.subtitle_cues[-1].end_ms == 3000
    assert all(
        left.end_ms == right.start_ms and left.end_ms > left.start_ms
        for left, right in zip(timing.subtitle_cues, timing.subtitle_cues[1:])
    )


def test_low_coverage_uses_whole_unit_text_length_fallback_with_rounding():
    unit = segment_script("甲乙， 丙丁丁。", target_sentences=2)[0]
    timing = time_voice_unit(unit, 701, _char_alignment(unit.text, coverage=0.5))

    assert timing.subtitle_timing_source is TimingSource.TEXT_LENGTH_FALLBACK
    assert timing.subtitle_alignment == {
        "status": "failed", "reason_code": "ALIGNMENT_LOW_COVERAGE",
    }
    assert [(cue.text, cue.start_ms, cue.end_ms) for cue in timing.subtitle_cues] == [
        ("甲乙，", 0, 300), (" 丙丁丁。", 300, 701),
    ]


def test_long_chinese_and_missing_whisper_char_timestamp_fall_back_without_loss():
    text = "甲" * 25 + "，乙" * 24 + "。"
    unit = segment_script(text, target_sentences=2, max_unit_chars=400)[0]
    alignment = _char_alignment(unit.text)
    starts = dict(alignment.starts_ms)
    del starts["char:22"]
    timing = time_voice_unit(unit, 8001, AlignmentResult(starts, 1.0, 0.9))

    assert timing.subtitle_timing_source is TimingSource.TEXT_LENGTH_FALLBACK
    assert timing.subtitle_alignment["reason_code"] == "SUBTITLE_ALIGNMENT_INCOMPLETE"
    assert "".join(cue.text for cue in timing.subtitle_cues) == text
    assert all(len("".join(cue.text.split())) <= 22 for cue in timing.subtitle_cues)
    assert timing.subtitle_cues[-1].end_ms == 8001


def test_fallback_merges_impossible_splits_to_avoid_zero_length_cues():
    unit = segment_script("甲。乙。丙。", target_sentences=3)[0]
    timing = time_voice_unit(unit, 2, None)

    assert "".join(cue.text for cue in timing.subtitle_cues) == unit.text
    assert [(cue.start_ms, cue.end_ms) for cue in timing.subtitle_cues] == [(0, 1), (1, 2)]


def test_composition_offsets_local_cues_and_exposes_manifest_and_srt(tmp_path: Path):
    units = [
        {
            "unit_id": "unit-1", "duration_ms": 701,
            "subtitle_timing_source": "text_length_fallback",
            "subtitle_alignment": {"status": "failed", "reason_code": "ALIGNMENT_LOW_COVERAGE"},
            "subtitle_cues": [
                {"text": "甲乙，", "start_ms": 0, "end_ms": 300},
                {"text": "丙丁。", "start_ms": 300, "end_ms": 701},
            ],
        },
        {
            "unit_id": "unit-2", "duration_ms": 299,
            "subtitle_timing_source": "whisper",
            "subtitle_alignment": {"status": "succeeded", "coverage": 1.0, "confidence": 0.9},
            "subtitle_cues": [{"text": "后续。", "start_ms": 0, "end_ms": 299}],
        },
    ]
    cues, subtitle_timing = CompositionService._subtitle_units(units, {})
    target = tmp_path / "subtitles.srt"
    CompositionService._generate_subtitles(None, cues, target)
    manifest = CompositionService._build_final_manifest(
        None, "task", "run", [], [], 1000, "output/final.mp4", "artifacts/subtitles.srt",
        subtitle_timing, {"passed": True},
    )

    assert [(cue["start_ms"], cue["end_ms"]) for cue in cues] == [(0, 300), (300, 701), (701, 1000)]
    assert "00:00:00,701 --> 00:00:01,000\n后续。" in target.read_text(encoding="utf-8")
    assert manifest["subtitle_timing"] == subtitle_timing
    assert manifest["quality"]["subtitle_cue_count"] == 3
    assert subtitle_timing[0]["fallback_reason"] == "ALIGNMENT_LOW_COVERAGE"
