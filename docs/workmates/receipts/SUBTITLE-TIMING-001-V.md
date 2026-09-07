# SUBTITLE-TIMING-001-V verification receipt

Verdict: **PASS**

## Frozen file hashes (SHA-256) — re-verified from main integration

| File | Receipt hash | Re-verified |
| --- | --- | --- |
| `csboard/domain/av_timing.py` | `63f5437c…3d701` | `63f5437c…3d701` ✅ |
| `csboard/domain/enums.py` | `1502ade3…cbe7` | `1502ade3…cbe7` ✅ |
| `csboard/application/av_artifacts.py` | `de22a83c…3b08` | `de22a83c…3b08` ✅ |
| `csboard/application/composition.py` | `73ce17c1…7ad5ad` | `73ce17c1…7ad5ad` ✅ |
| `schemas/timeline.schema.json` | `200076f9…9cf5` | `200076f9…9cf5` ✅ |
| `tests/test_subtitle_timing_001.py` | `bf0bf9cb…39549` | `bf0bf9cb…39549` ✅ |

## Criterion-to-evidence mapping

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Acceptance criteria mapped independently | ✅ | See independent kernel verification below |
| 2 | Targeted test suite | ✅ | 26 passed, 4 `RefResolver` deprecation warnings |
| 3 | Two Voice Units: Whisper success + fallback | ✅ | Unit A: Whisper, 4 cues, monotonic, boundary 6000. Unit B: text_length_fallback, 1 cue, boundary 800 |
| 4 | Fallback uses non-whitespace char weight, ends at unit boundary, no zero-length cue | ✅ | Unit B: 1 cue [0,800]. Unit C (5ms/long text): merged to 1 cue [0,5], end=5 |
| 5 | Timeline/final manifest has `subtitle_timing_source`, fallback reason, cue count | ✅ | manifest[0]: source=whisper, count=4. manifest[1]: source=text_length_fallback, reason=ALIGNMENT_LOW_COVERAGE, count=1 |
| 6 | Multi-unit SRT: cumulative offset, monotonic, no overlap, unit boundaries | ✅ | 5 SRT entries, unit-1 [0,6000), unit-2 [6000,6800), text complete per unit |
| 7 | git diff --check | ✅ | Exit 0, no whitespace errors |
| 8 | Workmates verify | ✅ | Exit 0, status PASS |

## Commands and exit codes

| Command | Exit |
|---------|------|
| `sha256sum` on 6 frozen files | 0 — all match |
| `pytest -q <5 test files>` | 0, 26 passed |
| Independent kernel verification script | 0 — all checks passed |
| `git diff --check` on 6 frozen targets | 0 |
| `./scripts/workmates verify --role verification --evidence ...` | 0, PASS |

## Independent kernel verification details

**Unit A — Whisper success path:**
- Text: `你好世界，这是一个测试。今天天气不错，我们出去走走吧！`
- Duration: 6000ms, alignment coverage=0.98, confidence=0.92
- Result: 4 subtitle cues, source=whisper
- Cues: `[0,1111)`, `[1111,2666)`, `[2666,4222)`, `[4222,6000)` — monotonic, no overlap, ends at boundary
- Text reconstructed = original ✅

**Unit B — Low coverage fallback:**
- Text: `短句。`, Duration: 800ms, alignment coverage=0.30
- Result: 1 cue, source=text_length_fallback
- Cue: `[0,800)` — ends exactly at unit boundary ✅

**Unit C — Extreme short duration (5ms, long text):**
- Text: `你好世界测试短文本内容比较多一些需要分段处理`, Duration: 5ms
- Result: 1 cue `[0,5)` — no zero-length cue ✅

**Multi-unit SRT composition via `_subtitle_units`:**
- 2 timeline units, 5 SRT entries total
- Unit-1: 4 entries, all in [0,6000), text complete ✅
- Unit-2: 1 entry, in [6000,6800), text complete ✅
- No cross-unit time borrowing ✅
- Manifest: timing_source/fallback_reason/cue_count correct per unit ✅

## Post-hash verification

Hashes re-verified at end of session — all 6 files unchanged.

## Unverified scope

- Real Whisper alignment data (only synthetic alignment used)
- Real provider invocation (not called per task constraints)
- Final video subtitle visual rendering (reserved for user)
- Old timeline compatibility fallback (covered by existing test suite)
