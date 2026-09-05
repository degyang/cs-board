# PRESET-VOICE-UX-001-FE — worker_frontend receipt

Status: COMPLETE — awaiting independent verification; no self-acceptance.

## Delivered

- Reworked the preset catalog into selectable Provider-backed profiles with add, edit, and save flows. Provider options come only from `fetchServices({ enabled: true })`, filtered by declared audio/TTS capability names; no vendor/provider constants are used for the choices.
- Moved generated audio out of cards/detail/form into a page-bottom, independently labelled试听区. It binds to the selected profile, has the exact required editable default text, disables with a selection prompt, calls `previewVoiceProfile(profile_id, text)`, and presents loading, success-audio, and error states.
- Invalidates and pauses prior preview audio on every selection change. A generation token prevents an old async response from replacing the newly selected profile's audio.
- Added front-end POST/PATCH helpers for provider-neutral preset profile create/edit and direct tests for capability filtering, create/edit/save, binding, default/custom text, request parameters, stale-audio invalidation, error, and successful-only audio rendering.

## Changed files (assignment boundary only)

- `web-v2/src/pages/VoiceManagementPage.tsx`
- `web-v2/src/lib/api/voiceProfiles.ts`
- `web-v2/tests/voice-management.test.tsx`
- `web-v2/tests/voice-profiles-api.test.ts`

## Verification

| Command | Exit | Result | Duration |
| --- | ---: | --- | ---: |
| `cd web-v2 && npm test -- --run tests/voice-management.test.tsx tests/voice-profiles-api.test.ts` | 0 | 2 files, 14 passed, 0 failed, 0 skipped | 7.49s |
| `cd web-v2 && npm run build` | 0 | TypeScript check and Vite build passed | 1.23s |
| `cd web-v2 && npm test` | 0 | 20 files, 444 passed, 0 failed, 0 skipped | 19.77s |

Known non-failing output: pre-existing React Router future-flag and `act(...)` warnings in unrelated test suites. No service process was restarted; no commit or push was made.
