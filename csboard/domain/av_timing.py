from __future__ import annotations

import re
from dataclasses import dataclass
from csboard.domain.enums import TimingSource
from csboard.domain.provider_types import AlignmentResult

__all__ = [
    "AlignmentResult",
    "TextRange",
    "SubtitleCue",
    "UnitTiming",
    "VisualItem",
    "VisualTiming",
    "VoiceUnit",
    "segment_script",
    "subtitle_fallback_cues",
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
class SubtitleCue:
    """A subtitle interval local to one Voice Unit."""

    text: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True, slots=True)
class UnitTiming:
    unit_id: str
    duration_ms: int
    timing_source: TimingSource
    visual_timings: tuple[VisualTiming, ...]
    alignment: dict[str, object]
    subtitle_cues: tuple[SubtitleCue, ...] = ()
    subtitle_timing_source: TimingSource = TimingSource.TEXT_LENGTH_FALLBACK
    subtitle_alignment: dict[str, object] | None = None


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
    subtitle_cues: tuple[SubtitleCue, ...] | None = None
    subtitle_reason = "ALIGNMENT_UNAVAILABLE"
    if alignment is not None:
        timings = _whisper_timings(unit, duration_ms, alignment, minimum_coverage, minimum_confidence)
        subtitle_cues = _whisper_subtitle_cues(
            unit, duration_ms, alignment, minimum_coverage, minimum_confidence,
        )
        subtitle_reason = _subtitle_fallback_reason(
            unit, duration_ms, alignment, minimum_coverage, minimum_confidence,
        )
        if timings is not None:
            subtitle_source = TimingSource.WHISPER if subtitle_cues is not None else TimingSource.TEXT_LENGTH_FALLBACK
            return UnitTiming(unit.unit_id, duration_ms, TimingSource.WHISPER, timings, {
                "status": "succeeded", "engine": alignment.engine,
                "coverage": alignment.coverage, "confidence": alignment.confidence,
            }, subtitle_cues or subtitle_fallback_cues(unit.text, duration_ms), subtitle_source, {
                "status": "succeeded" if subtitle_cues is not None else "failed",
                "engine": alignment.engine,
                "coverage": alignment.coverage,
                "confidence": alignment.confidence,
                **({"reason_code": subtitle_reason} if subtitle_cues is None else {}),
            })
    reason = alignment.reason_code if alignment and alignment.reason_code else "ALIGNMENT_UNAVAILABLE"
    return UnitTiming(unit.unit_id, duration_ms, TimingSource.EQUAL_FALLBACK, _equal_timings(unit, duration_ms), {
        "status": "failed", "reason_code": reason,
    }, subtitle_fallback_cues(unit.text, duration_ms), TimingSource.TEXT_LENGTH_FALLBACK, {
        "status": "failed", "reason_code": subtitle_reason,
    })


def subtitle_fallback_cues(text: str, duration_ms: int, max_chars: int = 22) -> tuple[SubtitleCue, ...]:
    """Split text deterministically and allocate one Voice Unit's actual duration.

    Whitespace is not weighted, but remains in the emitted text so subtitle
    content is lossless. Integer boundaries make the final cue end exactly at
    ``duration_ms`` without accumulating rounding error.
    """
    if duration_ms <= 0:
        raise ValueError("语音时长必须大于 0")
    chunks = _subtitle_chunks(text, max_chars)
    # A positive-duration SRT cue needs at least one millisecond. Preserve all
    # text by merging the final chunks if an unusually short voice cannot show
    # every readable split independently.
    while len(chunks) > duration_ms:
        left, right = chunks[-2:]
        chunks[-2:] = [(left[0] + right[0], left[1], right[2])]
    if not chunks:
        return ()
    weights = [max(1, _visible_length(chunk[0])) for chunk in chunks]
    total = sum(weights)
    distributable_ms = duration_ms - len(chunks)
    cursor = 0
    cues: list[SubtitleCue] = []
    for index, (chunk, _start, _end) in enumerate(chunks):
        end = duration_ms if index == len(chunks) - 1 else (
            index + 1 + (distributable_ms * sum(weights[:index + 1])) // total
        )
        cues.append(SubtitleCue(chunk, cursor, end))
        cursor = end
    return tuple(cues)


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
        raise ValueError("Voice Unit 未完整覆盖原文")
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


def _whisper_subtitle_cues(
    unit: VoiceUnit, duration_ms: int, result: AlignmentResult,
    min_coverage: float, min_confidence: float,
) -> tuple[SubtitleCue, ...] | None:
    if result.coverage < min_coverage or result.confidence < min_confidence:
        return None
    chunks = _subtitle_chunks(unit.text)
    if not chunks:
        return ()
    starts: list[int] = []
    for _text, start, end in chunks:
        value = _cue_start(result, unit.text, start, end)
        if value is None:
            return None
        starts.append(int(value))
    # A cue includes leading silence, just as a Visual Item does.
    starts[0] = 0
    if any(value < 0 or value >= duration_ms for value in starts):
        return None
    if any(starts[index] >= starts[index + 1] for index in range(len(starts) - 1)):
        return None
    return tuple(
        SubtitleCue(text, starts[index], starts[index + 1] if index + 1 < len(starts) else duration_ms)
        for index, (text, _start, _end) in enumerate(chunks)
    )


def _subtitle_fallback_reason(
    unit: VoiceUnit, duration_ms: int, result: AlignmentResult,
    min_coverage: float, min_confidence: float,
) -> str:
    if result.coverage < min_coverage:
        return result.reason_code or "ALIGNMENT_LOW_COVERAGE"
    if result.confidence < min_confidence:
        return result.reason_code or "ALIGNMENT_LOW_CONFIDENCE"
    chunks = _subtitle_chunks(unit.text)
    starts = [
        _cue_start(result, unit.text, start, end)
        for _text, start, end in chunks
    ]
    if any(value is None for value in starts):
        return result.reason_code or "SUBTITLE_ALIGNMENT_INCOMPLETE"
    numeric = [int(value) for value in starts if value is not None]
    if any(value < 0 or value >= duration_ms for value in numeric):
        return result.reason_code or "SUBTITLE_ALIGNMENT_OUT_OF_RANGE"
    return result.reason_code or "SUBTITLE_ALIGNMENT_NON_MONOTONIC"


def _subtitle_chunks(text: str, max_chars: int = 22) -> list[tuple[str, int, int]]:
    """Return lossless, punctuation-aware readable chunks with source ranges."""
    if not text:
        return []
    chunks: list[tuple[str, int, int]] = []
    start = 0
    visible = 0
    punctuation = "。！？!?；;，,"
    for index, char in enumerate(text):
        if not char.isspace():
            visible += 1
        boundary = char in punctuation or visible >= max_chars
        if boundary:
            end = index + 1
            if text[start:end].strip():
                chunks.append((text[start:end], start, end))
            start = end
            visible = 0
    if start < len(text):
        if text[start:].strip():
            chunks.append((text[start:], start, len(text)))
        elif chunks:
            previous = chunks[-1]
            chunks[-1] = (previous[0] + text[start:], previous[1], len(text))
    return chunks


def _cue_start(result: AlignmentResult, text: str, start: int, end: int) -> int | None:
    """Use the first spoken character of each cue as its real Whisper boundary."""
    index = next((index for index in range(start, end) if not text[index].isspace()), None)
    return result.starts_ms.get(f"char:{index}") if index is not None else None


def _visible_length(text: str) -> int:
    return sum(1 for char in text if not char.isspace())
