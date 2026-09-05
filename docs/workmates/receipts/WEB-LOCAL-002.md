# WEB-LOCAL-002 receipt

- Scope completed: `web-v2/src/pages/VoiceAlignmentPage.tsx`, its direct tests, and the route-contract fixture update.
- Delivered: explicit “本地服务” title; local speech-service list filtered to `speech_synthesis`, `speech_alignment`, and `indextts`; right-side detail/preview/edit state; create, edit/save, Secret handling, delete, and real `/services/:id/probe` action wiring.
- Probe refresh no longer unmounts the detail panel, so its returned availability result remains visible.
- Direct tests added in `web-v2/tests/voice-alignment-page.test.tsx`: list/filtering, detail preview switching, create, edit/save, and probe result.
- Verification: `cd web-v2 && npm test` — PASS, 20 files / 439 tests / 0 failed / 0 skipped.
- Verification: `cd web-v2 && npm run build` — PASS.
- Live check: restarted the single stale Vite listener at 5182. `GET /settings/voice-alignment` returns 200 and the served `VoiceAlignmentPage.tsx` contains the current preview and non-unmounting refresh code.
- No backend, dynamic-infographic, or unrelated baseline-page files were changed; no commit was made.
