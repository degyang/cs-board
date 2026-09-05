# M09-LOCAL-001 — Voice Alignment Local Services page

## Goal

Make `/settings/voice-alignment` a usable **Local Services** page with real interactions. Visually follow the preset-voice list/detail pattern from `VoiceManagementPage`. Whisper must NOT appear on this page (toolchain only) and must NOT appear on model services.

## Inputs

- Existing page: `web-v2/src/pages/VoiceAlignmentPage.tsx`
- Pattern reference: `web-v2/src/pages/VoiceManagementPage.tsx` (`PresetVoiceCatalog` — list/detail, grouped, preview)
- Backend APIs:
  - `GET /api/v1/settings/voice-alignment` — returns `{ speech_synthesis, speech_alignment, indextts, whisper }`
  - `GET /api/v1/services?capability=speech_synthesis&enabled=true` — list TTS services
  - `GET /api/v1/services?capability=speech_alignment&enabled=true` — list alignment services
  - `POST /api/v1/services` — create service (add)
  - `PATCH /api/v1/services/{id}` — update service (edit)
  - `POST /api/v1/services/{id}/probe` — probe/health check
  - `POST /api/v1/services/{id}/activate` / `deactivate` — toggle
  - `POST /api/v1/services/{id}/secrets` — set secrets
- Frontend API wrappers: `web-v2/src/lib/api/services.ts`, `web-v2/src/lib/api/settings.ts`
- Types: `web-v2/src/lib/api/types.ts` (`VoiceAlignmentSettings`, `ServiceDefinition`, etc.)
- CSS: `web-v2/src/styles/settings.css`

## Scope

### In scope

1. **List panel** (left side): show speech_synthesis and speech_alignment services grouped by capability, with display_name, status badge, and adapter_type. Selecting a service loads its detail.
2. **Detail panel** (right side): show service metadata (endpoint, model, adapter_type, capability), availability probe status (last checked, latency, error), and secret configuration status.
3. **Add interaction**: button opens a form (reuse `ServiceFormPage` pattern or inline modal) to create a new service with `capability=speech_synthesis` or `speech_alignment`. Required fields: `service_id`, `display_name`, `capability`, `adapter_type`, `endpoint`.
4. **Edit interaction**: from detail panel, edit display_name, endpoint, model, config. Use existing `PATCH /api/v1/services/{id}`.
5. **Probe interaction**: button calls `POST /api/v1/services/{id}/probe`, shows live result.
6. **Preview interaction**: for TTS services, call the voice-profile preview endpoint (`POST /api/v1/voice-profiles/{profile_id}/preview`) or, if no backend preview endpoint exists for raw services, **create a bounded backend subtask** (see M09-LOCAL-002 below) — do NOT build mock UI.
7. **Whisper exclusion**: filter out `capability=whisper` from all queries and display. Whisper belongs on toolchain page only.
8. **Router**: route at `settings/voice-alignment` is already registered — verify it works.
9. **Focused tests**: add or update a test file (e.g., `tests/test_voice_alignment_page.tsx` or equivalent) covering list rendering, add flow, edit flow, and probe interaction.
10. **Build**: `npm run build` in `web-v2/` passes with zero errors.

### Out of scope

- `web-v2` baseline alignment (lint, format, refactor) — do NOT touch.
- Dynamic infographic implementation — planning dependency only (record below).
- Model services page changes.
- Whisper page or whisper API changes.

## Planning dependency (record only)

> **Dynamic infographic implementation** depends on this local-services page being usable first, because infographic tasks reference TTS service availability and voice profiles that this page manages. Do not open infographic implementation until M09-LOCAL-001 is accepted.

## Constraints

- Do not commit.
- Do not alter any file outside `web-v2/src/` except board/receipt/assignment docs.
- Whisper must never appear in the voice-alignment page UI.
- If a TTS preview API for raw services (not voice profiles) does not exist, create `M09-LOCAL-002` as a bounded backend subtask and block the preview interaction on it. Do not mock the UI.

## Acceptance criteria (browser-visible at port 5182)

1. `/settings/voice-alignment` renders a list/detail layout with TTS and alignment services.
2. "Add service" opens a working form; submitting creates a real service visible on reload.
3. Clicking a service shows its detail; editing fields and saving persists via `PATCH`.
4. Probe button calls the real endpoint and updates the availability display.
5. Whisper never appears anywhere on the page.
6. `npm run build` in `web-v2/` exits 0.
7. Focused test(s) pass.

## Required output

Write `docs/workmates/receipts/M09-LOCAL-001.md` with:

1. Files changed (list with brief description).
2. Tests run and results (paste output).
3. Build result (`npm run build` output, last lines).
4. Pass/fail against each acceptance criterion.
5. Any API gaps found and whether M09-LOCAL-002 was created.
6. Next owner.

Then update only the matching row in `docs/workmates/board.md`.
