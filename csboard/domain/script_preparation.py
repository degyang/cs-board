"""Deterministic script preparation (文案整理).

Splits raw script text into Voice Units at task-creation / input-save time.
This is a pure, deterministic operation — no LLM involved.

Algorithm: split by sentence boundaries, then merge consecutive sentences
into units whose char count is as close to ``target_chars`` as possible,
respecting ``min_chars`` (won't start a new unit below this threshold) and
``max_chars`` (hard cap per unit).

Output is stored in task.json under the ``script_preparation`` field.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["prepare_script", "PREPARATION_ALGORITHM_VERSION"]

PREPARATION_ALGORITHM_VERSION = "deterministic-v1"

# Default rules — callers may override.
DEFAULT_TARGET_CHARS = 80
DEFAULT_MIN_CHARS = 35
DEFAULT_MAX_CHARS = 140


@dataclass(frozen=True, slots=True)
class _Sentence:
    start: int
    end: int
    text: str


def _split_sentences(text: str) -> list[_Sentence]:
    """Split text by Chinese/English sentence-ending punctuation."""
    sentences: list[_Sentence] = []
    start = 0
    for match in re.finditer(r"[。！？!?；;]", text):
        end = match.end()
        t = text[start:end]
        if t.strip():
            sentences.append(_Sentence(start, end, t))
        start = end
    # Trailing text without punctuation
    if start < len(text):
        t = text[start:]
        if t.strip():
            sentences.append(_Sentence(start, len(text), t))
    return sentences


def prepare_script(
    text: str,
    *,
    target_chars: int = DEFAULT_TARGET_CHARS,
    min_chars: int = DEFAULT_MIN_CHARS,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> dict:
    """Run deterministic script preparation and return the dict to embed in task.json.

    Parameters
    ----------
    text:
        Raw script text (文案).
    target_chars:
        Target characters per Voice Unit. The algorithm tries to make each
        unit as close to this size as possible.
    min_chars:
        Minimum characters for a unit. If adding the next sentence would
        push the unit above ``target_chars`` but the current unit is below
        ``min_chars``, the sentence is still added.
    max_chars:
        Hard cap. A unit will never exceed this size; if a single sentence
        exceeds ``max_chars`` it becomes its own unit.

    Returns
    -------
    dict
        ``{"algorithm_version": ..., "rules": ..., "voice_units": [...]}``
        ready to store under ``task.json["script_preparation"]``.

    Raises
    ------
    ValueError
        If text is empty or all-whitespace.
    """
    if not text or not text.strip():
        raise ValueError("文案不能为空")

    sentences = _split_sentences(text)
    if not sentences:
        raise ValueError("文案不能为空")

    voice_units: list[dict] = []
    cursor = 0  # index into sentences list

    while cursor < len(sentences):
        unit_start = cursor
        unit_char_count = len(sentences[cursor].text)

        # Greedily add sentences while we're under target_chars,
        # or if we haven't reached min_chars yet.
        while cursor + 1 < len(sentences):
            next_chars = len(sentences[cursor + 1].text)
            # Hard cap: stop if adding next sentence exceeds max_chars
            if unit_char_count + next_chars > max_chars:
                break
            # If we're already at/above target_chars and above min_chars, stop
            if unit_char_count >= target_chars and unit_char_count >= min_chars:
                break
            cursor += 1
            unit_char_count += len(sentences[cursor].text)

        # Build unit from sentences[unit_start .. cursor]
        selected = sentences[unit_start : cursor + 1]
        unit_order = len(voice_units) + 1
        source_start = selected[0].start
        source_end = selected[-1].end
        unit_text = text[source_start:source_end]

        voice_units.append({
            "unit_id": f"unit-{unit_order:03d}",
            "order": unit_order,
            "source_range": {"start": source_start, "end": source_end},
            "text": unit_text,
        })

        cursor += 1

    # Validate coverage: units must be contiguous and cover full text
    _validate_coverage(text, voice_units)

    return {
        "algorithm_version": PREPARATION_ALGORITHM_VERSION,
        "rules": {
            "target_chars": target_chars,
            "min_chars": min_chars,
            "max_chars": max_chars,
        },
        "voice_units": voice_units,
    }


def _validate_coverage(text: str, voice_units: list[dict]) -> None:
    """Ensure units are contiguous and cover the full text."""
    if not voice_units:
        raise ValueError("文案分割未产生任何 Voice Unit")
    if voice_units[0]["source_range"]["start"] != 0:
        raise ValueError("Voice Unit 原文范围未从 0 开始")
    if voice_units[-1]["source_range"]["end"] != len(text):
        raise ValueError("Voice Unit 原文范围未覆盖到文案末尾")
    expected = 0
    for unit in voice_units:
        if unit["source_range"]["start"] != expected:
            raise ValueError("Voice Unit 原文范围不连续")
        expected = unit["source_range"]["end"]
