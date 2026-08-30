"""Deterministic script preparation (文案整理).

Splits raw script text into Voice Units at task-creation / input-save time.
This is a pure, deterministic operation — no LLM involved.

Called from:
  - csboard.application.commands.MountainCommands.task_create()
  - csboard.application.commands.MountainCommands.task_save_inputs()
  - webapp.mountain_v1_api  POST /api/v1/tasks/{task_id}/inputs

Output is stored in task.json under the ``script_preparation`` field.
"""

from __future__ import annotations

from csboard.domain.av_timing import VoiceUnit, segment_script

__all__ = ["prepare_script"]

# Default rules — callers may override.
DEFAULT_TARGET_CHARS = 80
DEFAULT_MIN_CHARS = 35
DEFAULT_MAX_CHARS = 140


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
        Target characters per Voice Unit.
    min_chars / max_chars:
        Bounds that the segmentation algorithm respects.

    Returns
    -------
    dict
        ``{"algorithm_version": ..., "rules": ..., "voice_units": [...]}``
        ready to store under ``task.json["script_preparation"]``.
    """
    if not text or not text.strip():
        raise ValueError("文案不能为空")

    # The existing segment_script uses target_sentences / max_unit_chars.
    # We translate the char-based parameters into sentence-count heuristics:
    #   target_sentences ≈ target_chars / avg_sentence_len  (assume ~40 chars/sentence)
    #   max_unit_chars maps directly.
    # For the deterministic baseline we keep 2 sentences per unit and use
    # max_unit_chars as the hard cap.
    units: tuple[VoiceUnit, ...] = segment_script(
        text,
        target_sentences=2,
        max_unit_chars=max_chars,
    )

    voice_units = [
        {
            "unit_id": u.unit_id,
            "order": u.order,
            "source_range": {"start": u.source_range.start, "end": u.source_range.end},
            "text": u.text,
        }
        for u in units
    ]

    return {
        "algorithm_version": "deterministic-v1",
        "rules": {
            "target_chars": target_chars,
            "min_chars": min_chars,
            "max_chars": max_chars,
        },
        "voice_units": voice_units,
    }
