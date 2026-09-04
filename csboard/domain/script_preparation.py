"""Paragraph-first deterministic script preparation.

The sole segmentation authority. Raw offsets are Unicode code-point,
zero-based, half-open ranges; Voice Units contain normalized, newline-free text.
"""
from __future__ import annotations

import re
import unicodedata

__all__ = ["prepare_script", "PREPARATION_ALGORITHM_VERSION"]

PREPARATION_ALGORITHM_VERSION = "paragraph-first-v2"
DEFAULT_TARGET_CHARS, DEFAULT_MIN_CHARS, DEFAULT_MAX_CHARS = 80, 35, 140
_CLOSERS = "”’」』）》】>)]}"
_COMMON_ABBREVIATIONS = {"dr", "mr", "mrs", "ms", "prof", "vs", "etc", "e.g", "i.e", "u.s", "u.k", "fig", "no", "inc", "ltd"}
_WEAK_BOUNDARIES = "；;，,、：:—"


def _normalise_paragraphs(raw: str) -> tuple[list[dict], str, list[dict]]:
    """Normalize CR variants, isolate trimmed paragraphs, retain raw mapping."""
    logical: list[tuple[str, int, int]] = []
    index = 0
    while index < len(raw):
        if raw[index] == "\r":
            end = index + 2 if index + 1 < len(raw) and raw[index + 1] == "\n" else index + 1
            logical.append(("\n", index, end)); index = end
        else:
            logical.append((raw[index], index, index + 1)); index += 1
    paragraphs, ignored = [], []
    start = 0
    i = 0
    while i <= len(logical):
        if i < len(logical) and logical[i][0] != "\n":
            i += 1; continue
        chars = logical[start:i]
        if chars:
            original = "".join(item[0] for item in chars)
            left, right = len(original) - len(original.lstrip()), len(original.rstrip())
            if left < right:
                kept = chars[left:right]
                paragraphs.append({"text": "".join(item[0] for item in kept), "raw_range": {"start": kept[0][1], "end": kept[-1][2]}})
                if left: ignored.append({"start": chars[0][1], "end": chars[left - 1][2], "reason": "layout-whitespace"})
                if right < len(chars): ignored.append({"start": chars[right][1], "end": chars[-1][2], "reason": "layout-whitespace"})
            else:
                ignored.append({"start": chars[0][1], "end": chars[-1][2], "reason": "whitespace-only-paragraph"})
        if i == len(logical): break
        run_start, run_end = logical[i][1], logical[i][2]
        i += 1
        while i < len(logical) and logical[i][0] == "\n": run_end, i = logical[i][2], i + 1
        ignored.append({"start": run_start, "end": run_end, "reason": "paragraph-boundary"})
        start = i
    cursor = 0
    for number, paragraph in enumerate(paragraphs, 1):
        paragraph["paragraph_index"] = number
        paragraph["normalized_range"] = {"start": cursor, "end": cursor + len(paragraph["text"])}
        cursor += len(paragraph["text"]) + 1
    return paragraphs, "\n".join(item["text"] for item in paragraphs), ignored


def _period_is_sentence_end(text: str, index: int) -> bool:
    before = text[index - 1] if index else ""
    after = text[index + 1] if index + 1 < len(text) else ""
    if before.isdigit() and after.isdigit(): return False
    token_start = max(text.rfind(" ", 0, index), text.rfind("\t", 0, index)) + 1
    token = text[token_start:index + 1]
    lower = token.lower()
    if "@" in token or "://" in token or "/" in token or "\\" in token or (token.count(".") > 1 and not token.endswith("...")): return False
    if lower.rstrip(".") in _COMMON_ABBREVIATIONS or re.fullmatch(r"(?:[A-Za-z]\.)+[A-Za-z]?", token): return False
    pos = index + 1
    while pos < len(text) and text[pos] in _CLOSERS: pos += 1
    return pos == len(text) or text[pos].isspace()


def _strong_sentences(text: str) -> list[str]:
    pieces, start, i = [], 0, 0
    while i < len(text):
        char = text[i]
        is_end = char in "。！？…" or (char in "!?" and (i + 1 == len(text) or text[i + 1] in "!?" + _CLOSERS or text[i + 1].isspace())) or (char == "." and _period_is_sentence_end(text, i))
        if not is_end: i += 1; continue
        if char in "!?":
            while i + 1 < len(text) and text[i + 1] in "!?": i += 1
        elif char == "." and text[i:i + 3] == "...": i += 2
        elif char == "…" and text[i:i + 2] == "……": i += 1
        while i + 1 < len(text) and text[i + 1] in _CLOSERS: i += 1
        # Preserve ordinary inter-sentence whitespace.  It remains inside a
        # packed Voice Unit instead of being silently deleted by parsing.
        pieces.append(text[start:i + 1]); start = i + 1; i += 1
    if start < len(text) and text[start:].strip(): pieces.append(text[start:])
    return pieces


def _graphemes(value: str) -> list[str]:
    clusters: list[str] = []
    for char in value:
        if clusters and (unicodedata.combining(char) or char in "\ufe0e\ufe0f" or clusters[-1].endswith("\u200d")): clusters[-1] += char
        elif char == "\u200d" and clusters: clusters[-1] += char
        else: clusters.append(char)
    return clusters


def _split_over_max(sentence: str, maximum: int) -> list[tuple[str, str | None]]:
    if len(sentence) <= maximum: return [(sentence, None)]
    remaining, result = sentence, []
    while len(remaining) > maximum:
        candidates = [i + 1 for i, char in enumerate(remaining[:maximum]) if char in _WEAK_BOUNDARIES or char.isspace()]
        if candidates:
            cut = max(candidates); result.append((remaining[:cut].strip(), "weak-boundary")); remaining = remaining[cut:].strip(); continue
        if re.fullmatch(r"\S+", remaining) and re.search(r"[A-Za-z@/:.]", remaining): return result + [(remaining, "unbreakable-token-over-max")]
        clusters = _graphemes(remaining)
        result.append(("".join(clusters[:maximum]), "grapheme-fallback")); remaining = "".join(clusters[maximum:])
    if remaining: result.append((remaining, None))
    return result


def _pack_paragraph(atoms: list[tuple[str, str | None]], target: int, minimum: int, maximum: int) -> list[tuple[str, str | None, str | None]]:
    """Pack in source order; max is a hard constraint even below min."""
    groups: list[tuple[list[tuple[str, str | None]], str | None]] = []
    current: list[tuple[str, str | None]] = []
    current_len = 0
    for atom in atoms:
        projected = current_len + len(atom[0])
        if current and projected > maximum:
            groups.append((current, "hard-max")); current, current_len = [], 0
        elif current and projected > target and current_len >= minimum:
            groups.append((current, None)); current, current_len = [], 0
        current.append(atom); current_len += len(atom[0])
    if current: groups.append((current, None))
    if len(groups) > 1 and sum(len(item[0]) for item in groups[-1][0]) < minimum:
        tail, tail_reason = groups[-1]
        prior, prior_reason = groups[-2]
        if sum(len(item[0]) for item in prior + tail) <= maximum:
            groups[-2] = (prior + tail, prior_reason); groups.pop()
        elif len(prior) > 1:
            groups[-2], groups[-1] = (prior[:-1], prior_reason), (prior[-1:] + tail, tail_reason)
    packed = []
    for group, group_reason in groups:
        text = "".join(item[0] for item in group)
        split_reason = next((item[1] for item in group if item[1]), None) or group_reason
        undersize_reason = "hard-max" if len(text.strip()) < minimum and group_reason == "hard-max" else None
        packed.append((text, split_reason, undersize_reason))
    return packed


def prepare_script(text: str, *, target_chars: int = DEFAULT_TARGET_CHARS, min_chars: int = DEFAULT_MIN_CHARS, max_chars: int = DEFAULT_MAX_CHARS) -> dict:
    if not isinstance(text, str) or not text.strip(): raise ValueError("文案不能为空")
    if not (0 < min_chars <= max_chars and target_chars > 0): raise ValueError("文案分段规则无效")
    paragraphs, processing, ignored = _normalise_paragraphs(text)
    if not paragraphs: raise ValueError("文案不能为空")
    units: list[dict] = []
    for paragraph in paragraphs:
        atoms = [atom for sentence in _strong_sentences(paragraph["text"]) for atom in _split_over_max(sentence, max_chars)]
        offset, search = paragraph["normalized_range"]["start"], 0
        for packed_text, split_reason, pack_undersize_reason in _pack_paragraph(atoms, target_chars, min_chars, max_chars):
            left = len(packed_text) - len(packed_text.lstrip())
            unit_text = packed_text.strip()
            local_start = paragraph["text"].find(unit_text, search)
            if local_start < 0:
                raise ValueError("文案分段映射失败")
            local_end = local_start + len(unit_text); search = local_end
            units.append({"unit_id": f"unit-{len(units) + 1:03d}", "order": len(units) + 1, "text": unit_text,
                "paragraph_index": paragraph["paragraph_index"], "source_range": {"start": paragraph["raw_range"]["start"] + local_start, "end": paragraph["raw_range"]["start"] + local_end},
                "normalized_range": {"start": offset + local_start, "end": offset + local_end}, "boundary_reason": split_reason or ("paragraph" if local_start == 0 else "strong-sentence"),
                "undersize_reason": (pack_undersize_reason or "paragraph-boundary") if len(unit_text) < min_chars else None})
    return {"algorithm_version": PREPARATION_ALGORITHM_VERSION, "rules": {"target_chars": target_chars, "min_chars": min_chars, "max_chars": max_chars}, "raw_script": text,
        "normalized_processing_text": processing, "source_mapping": {"index_unit": "unicode-code-point", "range_semantics": "zero-based, end-exclusive", "raw_length": len(text), "normalized_length": len(processing),
        "paragraphs": [{key: value for key, value in item.items() if key != "text"} for item in paragraphs],
        "raw_to_normalized": [{"raw_range": item["raw_range"], "normalized_range": item["normalized_range"]} for item in paragraphs],
        "normalized_to_raw": [{"normalized_range": item["normalized_range"], "raw_range": item["raw_range"]} for item in paragraphs],
        "ignored_raw_ranges": ignored}, "voice_units": units}
