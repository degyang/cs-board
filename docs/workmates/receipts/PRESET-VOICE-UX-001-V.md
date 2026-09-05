# PRESET-VOICE-UX-001-V — Independent verification

Status: **FAIL** — the required user-facing “新增预置音色” path cannot create a profile against the real backend contract.

## Independent evidence

| Requirement | Evidence | Verdict |
| --- | --- | --- |
| Provider list is capability-derived, without vendor constants | Inspected `VoiceManagementPage.tsx`: `fetchServices({ enabled: true })` is filtered by normalized declared audio/TTS capability values and rendered from each service’s `service_id`/`display_name`; the preset API helpers contain no manufacturer constant. Focused UI tests cover filtering. | PASS |
| Select, edit, save, independent bottom试听区, editable default text | Inspected component and focused UI tests: cards set selection; edit uses PATCH; the only generated preview `<audio>` is within the bottom `aria-label="独立试听区"`; it is bound to selection and the exact required default text is editable. | PASS (static/automated evidence) |
| Real preview request/state/stale audio | Inspected `previewVoiceProfile(profileId, text)` POST, loading/error rendering, `audioRef.pause()`, clearing URL, and generation-token check. Focused test confirms profile/text arguments, failure state, and late old result suppression. Backend focused test verifies adapter `voice_id`, WAV format, controlled artifact response, and failure redaction/removal. No external Provider credentials were used; success evidence is adapter-mocked rather than an external Provider success. | PASS for application contract; external-provider live success not asserted |
| Stable identity/deduplication | `pytest -q tests/test_voice_profiles_api.py` independently passed; inspected NFKC/trim/casefold key `service_id|model_id|remote_voice_id`, deterministic precedence/order, post-dedupe totals, and tests for MiMo duplicate sources, same-name/different-model, rebuild stability, adapter request and safe failure. | PASS |
| Add a preset profile through the delivered UI/API contract | The form sends `name`, `provider_id`, `model_id`, `remote_voice_id`, etc., but no `profile_id`. `VoiceProfileCatalog.create_profile()` requires `_safe_id(payload["profile_id"])`. Independent real in-process API probe with an enabled, credential-configured `speech_synthesis` service submitted precisely that UI-shaped body: `POST /api/v1/voice-profiles` returned **400** `{ "detail": "profile id must be a simple identifier" }`. The UI test mocks `createPresetVoiceProfile` and therefore does not exercise this contract. | **FAIL** |

## Commands run

| Command | Exit | Result | Duration |
| --- | ---: | --- | ---: |
| `pytest -q tests/test_voice_profiles_api.py` | 0 | 8 passed, 0 failed, 0 skipped | 2.72s |
| `pytest -q tests/test_openai_tts_adapter.py tests/test_dynamic_provider_factory.py tests/test_mountain_api.py` | 0 | 25 passed, 0 failed, 0 skipped | 1.73s |
| `cd web-v2 && npm test -- --run tests/voice-management.test.tsx tests/voice-profiles-api.test.ts` | 0 | 2 files, 14 passed, 0 failed, 0 skipped | 7.26s |
| `cd web-v2 && npm run build` | 0 | TypeScript and Vite production build passed | 1.27s |
| `cd web-v2 && npm test -- --reporter=dot` | 0 | 20 files, 444 passed, 0 failed, 0 skipped | 20.18s |

Existing React Router future-flag and unrelated `act(...)` warnings occurred in the full frontend suite; they did not fail tests. No service was restarted, no dynamic-infographic render was executed, and no implementation or planning file was changed.

## Required correction

Make the frontend/backend create contract coherent: either have the backend generate and return a stable `profile_id` from the accepted provider/model/remote-voice identity, or explicitly collect/generate a valid client `profile_id` before POST. Add a non-mocked frontend-to-backend contract/integration regression test for creation, then rerun the listed gates.
