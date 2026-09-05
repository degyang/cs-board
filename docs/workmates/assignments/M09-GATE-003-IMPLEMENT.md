# M09-GATE-003 — Restore unsupported-capability regression + document behavior change

## Inputs

- PM decision: `docs/workmates/receipts/M09-GATE-001-V-DECIDE.md`
- Work board: `docs/workmates/board.md`
- Target file: `tests/test_dynamic_provider_factory.py`

## Context

The old test `test_unsupported_capability_for_openai` asserted that `openai_compatible` + `speech_synthesis` raised `UNSUPPORTED_ADAPTER`. That test was correctly removed (gate policy forbids skips) and replaced by `test_openai_speech_capability_creates_tts_adapter`, which asserts the combination now succeeds — reflecting the real behavior change in `provider_factory.py` lines 544–550.

However, the `UNSUPPORTED_ADAPTER` error path for `openai_compatible` with a genuinely unsupported capability lost its regression coverage.

## Task

### 1. Add regression test for truly unsupported capability

Add a new test in `tests/test_dynamic_provider_factory.py` that asserts `openai_compatible` with a capability that is NOT one of `text_generation`, `image_generation`, `speech_synthesis`, or `audio_generation` raises `DomainError` with code `UNSUPPORTED_ADAPTER`.

Suggested capability value: `"video_generation"` (genuinely unsupported by the current factory).

### 2. Document behavior change in existing test

Update the docstring of `test_openai_speech_capability_creates_tts_adapter` to note:
- This is a supported combination as of the TTS adapter addition.
- Previously this raised `UNSUPPORTED_ADAPTER`; the old regression test was removed and replaced by this one.

### 3. Run focused tests

```
python -m pytest tests/test_dynamic_provider_factory.py -v
```

All tests must pass, including the new regression test.

## Constraints

- Only `tests/test_dynamic_provider_factory.py` may be changed.
- Implementation changes to `provider_factory.py` are permitted only if the test reveals a gap (unlikely — the `else` branch at line 552 already handles this).
- Do not alter `web-v2/`.
- Do not commit.

## Required output

Write `docs/workmates/receipts/M09-GATE-003.md` with:

1. tests run and results (paste output);
2. file changed (exact diff or description);
3. pass/fail against verification criteria;
4. next owner.

Then update only the matching row in `docs/workmates/board.md`.
