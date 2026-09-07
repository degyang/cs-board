# PRESET-VOICE-UX-004-V-R — 真实试听错误终态补证

状态：dispatch_pending
Owner：verification（Claude Code `mimo-v2.5-pro / medium`）
模式：read-only browser evidence

## Goal

Close only the missing PRESET-VOICE-UX-004 hard-gate evidence: on current
integration 5182, safely trigger the audition action for an existing preset
and record its actual network request/response plus the visible terminal UI
state. The current environment may prove the allowed **visible real error**
terminal when no TTS provider is available; do not fabricate success, timeout,
or a provider.

## Scope and constraints

Use the Chromium path already named in `PRESET-VOICE-UX-004-FE.md`. Inspect
only and write one fresh screenshot under `/tmp` plus
`docs/workmates/receipts/PRESET-VOICE-UX-004-V-R.md`. Do not create/edit/delete
profiles, persist task data, change implementation/tests/services/topology or
the board, restart processes, submit a preview request more than once, commit,
or push. Capture viewport, selected preset, request URL/method, sanitized
status/body/error code, button/loading-to-terminal transition, and screenshot
path. Verify switching has no pre-existing audio before the single request;
do not claim success/timeout/switch coverage beyond what is actually observed.

Verdict is PASS only if the single real request reaches an allowed visible
terminal state without indefinite loading or stale audio. Otherwise FAIL or
BLOCKED with exact evidence. Stop after receipt; PM alone consumes it.
