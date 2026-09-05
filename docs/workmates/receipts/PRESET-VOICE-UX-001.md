# PRESET-VOICE-UX-001 — PM decision

Status: **CHANGES_REQUIRED — visual verification failed**

Consumed independent receipt `PRESET-VOICE-UX-001-V.md`. It independently passed capability-derived Provider choices, card/edit/independent试听区 behavior, preview state isolation, and backend identity/deduplication; all listed test and build gates exited 0.

Acceptance is denied because the delivered UI create payload omits `profile_id`, while the real backend `create_profile` contract requires it. The verifier submitted the UI-shaped payload to the in-process API and received HTTP 400 (`profile id must be a simple identifier`). The existing frontend test mocks this contract and cannot close the user-facing add gate.

The bounded backend correction `PRESET-VOICE-UX-002-BE` generated the stable ID server-side and added the in-process API regression. Independent re-verification in `PRESET-VOICE-UX-002-V.md` passed: a UI-shaped request without `profile_id` returned a stable valid ID; duplicate/rebuild/non-collision and MiMo dedupe checks passed; backend 9/9 + 25/25, frontend focused 14/14 + full 444/444, and build all exited 0 with no skips.

The user revoked WebUI acceptance because API and test evidence does not substitute for visible 5182 behavior. `PRESET-VOICE-UX-003-FE` produced browser evidence, then `PRESET-VOICE-UX-003-V` independently failed the actual 5182 edit flow: create POST returned 200 and rendered a card, but editing it returned PATCH 400, left the form open, and did not update the visible name. The preview success/error/old-audio checks passed but cannot close the required edit gate. No ACCEPTED decision is made. Dynamic-infographic planning remains unchanged.

User screenshot review additionally rejects the 003 visual result: the right detail column is unusably narrow, its text breaks vertically, and the full-page view does not clearly show the bottom independent preview area. `PRESET-VOICE-UX-004-FE` is active for desktop layout, full-page screenshot evidence, and a real preview terminal-state correction. Status remains REOPENED/FAIL; no ACCEPTED decision is permitted.
