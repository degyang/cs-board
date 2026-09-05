# M09-GATE-001-V — PM Decision (corrective)

**Date**: 2026-09-05
**Decision**: **approve with corrective assignment**

---

## Context

The verifier found that the old test `test_unsupported_capability_for_openai` (which asserted `UNSUPPORTED_ADAPTER` for `openai_compatible` + `speech_synthesis`) was removed and replaced by `test_openai_speech_capability_creates_tts_adapter`, which asserts the combination now succeeds.

This is **not a failure**. Gate policy forbids skips; the legacy skip was correctly removed. The behavior change is real: `provider_factory.py` lines 544–550 now route `openai_compatible` + `speech_synthesis` (and `audio_generation`) to `OpenAITTSAdapter`. The `else` branch at line 552 still raises `UNSUPPORTED_ADAPTER` for genuinely unsupported capabilities.

## What is missing

1. **Regression coverage for `UNSUPPORTED_ADAPTER`**: The removed test was the only assertion that `openai_compatible` with a truly unsupported capability (not `text_generation`, `image_generation`, `speech_synthesis`, or `audio_generation`) raises `UNSUPPORTED_ADAPTER`. A replacement test using a genuinely unsupported capability (e.g., `video_generation`) is required.

2. **Documented behavior change**: The new test's docstring should note that `openai_compatible` + `speech_synthesis` is now a supported combination (previously it raised `UNSUPPORTED_ADAPTER`).

## Corrective assignment

Create `M09-GATE-003` — bounded to `tests/test_dynamic_provider_factory.py` and its direct implementation only if needed.

## Next owner

`worker_backend` — see `M09-GATE-003-IMPLEMENT.md`.
