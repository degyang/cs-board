from __future__ import annotations

import re
from dataclasses import dataclass
from csboard.domain.enums import TimingSource
from csboard.domain.provider_types import AlignmentResult

__all__ = [
    "AlignmentResult",
    "TextRange",
    "UnitTiming",
    "VisualItem",
    "VisualTiming",
    "VoiceUnit",
    "segment_script",
    "time_voice_unit",
]


@dataclass(frozen=True, slots=True)
class TextRange:
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class VisualItem:
    visual_id: str
    order: int
    source_range: TextRange
    text: str


@dataclass(frozen=True, slots=True)
class VoiceUnit:
    unit_id: str
    order: int
    source_range: TextRange
    text: str
    visual_items: tuple[VisualItem, ...]


@dataclass(frozen=True, slots=True)
class VisualTiming:
    visual_id: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True, slots=True)
class UnitTiming:
    unit_id: str
    duration_ms: int
    timing_source: TimingSource
    visual_timings: tuple[VisualTiming, ...]
    alignment: dict[str, object]


def segment_script(text: str, target_sentences: int = 2, max_unit_chars: int = 260) -> tuple[VoiceUnit, ...]:
    """Deterministic safe baseline; later model planning may replace grouping, never ranges."""
    if not text:
        raise ValueError("文案不能为空")
    sentences = _sentence_ranges(text)
    units: list[VoiceUnit] = []
    cursor = 0
    while cursor < len(sentences):
        start_index = cursor
        end_index = cursor + 1
        while end_index < len(sentences) and end_index - start_index < target_sentences:
            candidate_end = sentences[end_index].end
            if candidate_end - sentences[start_index].start > max_unit_chars:
                break
            end_index += 1
        selected = sentences[start_index:end_index]
        unit_order = len(units) + 1
        visual_items = tuple(
            VisualItem(
                visual_id=f"visual-{unit_order:03d}-{index:02d}",
                order=index,
                source_range=item,
                text=text[item.start:item.end],
            )
            for index, item in enumerate(selected, 1)
        )
        source_range = TextRange(selected[0].start, selected[-1].end)
        units.append(VoiceUnit(
            unit_id=f"unit-{unit_order:03d}", order=unit_order,
            source_range=source_range, text=text[source_range.start:source_range.end], visual_items=visual_items,
        ))
        cursor = end_index
    _validate_coverage(text, units)
    return tuple(units)


def time_voice_unit(
    unit: VoiceUnit,
    duration_ms: int,
    alignment: AlignmentResult | None,
    minimum_coverage: float = 0.95,
    minimum_confidence: float = 0.70,
) -> UnitTiming:
    if duration_ms <= 0:
        raise ValueError("语音时长必须大于 0")
    if alignment is not None:
        timings = _whisper_timings(unit, duration_ms, alignment, minimum_coverage, minimum_confidence)
        if timings is not None:
            return UnitTiming(unit.unit_id, duration_ms, TimingSource.WHISPER, timings, {
                "status": "succeeded", "engine": alignment.engine,
                "coverage": alignment.coverage, "confidence": alignment.confidence,
            })
    reason = alignment.reason_code if alignment and alignment.reason_code else "ALIGNMENT_UNAVAILABLE"
    return UnitTiming(unit.unit_id, duration_ms, TimingSource.EQUAL_FALLBACK, _equal_timings(unit, duration_ms), {
        "status": "failed", "reason_code": reason,
    })


def _sentence_ranges(text: str) -> list[TextRange]:
    ranges: list[TextRange] = []
    start = 0
    for match in re.finditer(r"[。！？!?；;]", text):
        end = match.end()
        ranges.append(TextRange(start, end))
        start = end
    if start < len(text):
        ranges.append(TextRange(start, len(text)))
    return [item for item in ranges if text[item.start:item.end].strip()]


def _validate_coverage(text: str, units: tuple[VoiceUnit, ...]) -> None:
    if not units or units[0].source_range.start != 0 or units[-1].source_range.end != len(text):
        raise ValueError("文案分割未完整覆盖原文")
    expected = 0
    for unit in units:
        if unit.source_range.start != expected:
            raise ValueError("Voice Unit 原文范围不连续")
        expected = unit.source_range.end
        visual_expected = unit.source_range.start
        for visual in unit.visual_items:
            if visual.source_range.start != visual_expected:
                raise ValueError("Visual Item 原文范围不连续")
            visual_expected = visual.source_range.end
        if visual_expected != unit.source_range.end:
            raise ValueError("Visual Item 未完整覆盖 Voice Unit")


def _whisper_timings(unit: VoiceUnit, duration_ms: int, result: AlignmentResult, min_coverage: float, min_confidence: float) -> tuple[VisualTiming, ...] | None:
    if result.coverage < min_coverage or result.confidence < min_confidence:
        return None
    starts = [
        result.starts_ms.get(
            item.visual_id,
            result.starts_ms.get(f"char:{item.source_range.start - unit.source_range.start}"),
        )
        for item in unit.visual_items
    ]
    # A clip always starts at t=0 even when Whisper reports leading silence.
    if starts:
        starts[0] = 0
    if starts[0] != 0 or any(value is None or value < 0 or value >= duration_ms for value in starts):
        return None
    if any(int(starts[index]) >= int(starts[index + 1]) for index in range(len(starts) - 1)):
        return None
    return tuple(VisualTiming(item.visual_id, int(starts[index]), int(starts[index + 1]) if index + 1 < len(starts) else duration_ms) for index, item in enumerate(unit.visual_items))


def _equal_timings(unit: VoiceUnit, duration_ms: int) -> tuple[VisualTiming, ...]:
    count = len(unit.visual_items)
    return tuple(VisualTiming(item.visual_id, (index * duration_ms) // count, ((index + 1) * duration_ms) // count) for index, item in enumerate(unit.visual_items))
