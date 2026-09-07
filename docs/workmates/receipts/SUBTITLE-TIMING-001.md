# SUBTITLE-TIMING-001 backend receipt

Status: `READY_FOR_VERIFY`

## Delivered scope

- Voice Unit timing now persists lossless punctuation-aware subtitle cues in
  `timing.timeline`, with a separate `subtitle_timing_source` and visible
  alignment/fallback reason.
- Valid Whisper character boundaries create monotonic, unit-local subtitle
  cues. Low coverage, invalid/missing boundaries, exceptions, and unavailable
  alignment use one whole-unit `text_length_fallback`; no unit mixes sources.
- Fallback divides the actual Voice Unit duration by non-whitespace subtitle
  character weight, preserves text, ends exactly at the unit boundary, and
  merges impossible sub-millisecond splits to avoid zero-length cues.
- Composition consumes local cues, adds only cumulative Voice Unit offsets for
  SRT, validates local coverage, and exposes per-unit subtitle timing/fallback
  data plus cue count in the final manifest.

## Verification

| Command | Exit | Result |
| --- | ---: | --- |
| `.venv/bin/python -m pytest -q tests/test_subtitle_timing_001.py tests/test_av_timing.py tests/test_voice_units.py tests/test_composition_service.py tests/test_mountain_contracts.py` | 0 | 26 passed; 4 existing `jsonschema.RefResolver` deprecation warnings |
| `git diff --check` | 0 | clean |

The targeted tests use fake/in-memory media and synthetic alignment data only.
They do not call a provider or create real user content.

## File hashes (SHA-256)

| File | SHA-256 |
| --- | --- |
| `csboard/domain/av_timing.py` | `63f5437c04bab7f80535eb4a8d6e5a65decf64a01a30d5755ae518f81ae3d701` |
| `csboard/domain/enums.py` | `1502ade356947d96c6a2d2c7c2b529e679ca520ac784fb069c2dbc2dc779cbe7` |
| `csboard/application/av_artifacts.py` | `de22a83c7f53975e38cc85f016e7991e9facf4063ef511465902585a6dbb3b08` |
| `csboard/application/composition.py` | `73ce17c1abc47ae9daddd3c8360d21d11086b694ff56499c587ec62d077ad5ad` |
| `schemas/timeline.schema.json` | `200076f9b14ef3817ab3d71d28e795394992c30f1de985277e086ed2aace9cf5` |
| `tests/test_subtitle_timing_001.py` | `bf0bf9cb7ef59ba83d9fcc203b7b5d8a64e3b2db99a390c5876825d176c39549` |

No M09-ACTIVATE-005 file was changed. No commit, merge, push, service setting,
secret, provider invocation, or real user-content generation was performed.
