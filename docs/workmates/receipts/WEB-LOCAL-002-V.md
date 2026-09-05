# WEB-LOCAL-002 independent verification receipt

## Verdict: FAIL

The explicit Whisper exclusion gate fails against the live service data. No implementation files were modified during verification.

## Evidence

| Check | Command / method | Result |
| --- | --- | --- |
| File boundary | `git diff --name-only -- web-v2`; inspected untracked page test | PASS. Direct WebUI changes are `src/pages/VoiceAlignmentPage.tsx`, `tests/services-contract.test.tsx`, and `tests/voice-alignment-page.test.tsx`; no backend or unrelated WebUI implementation file is in this ticket's WebUI diff. `git diff --check` exit 0. |
| List/detail preview, add, edit | Independent source and direct-test inspection; `tests/voice-alignment-page.test.tsx` | PASS. The test covers list selection/detail preview, creation, editing/save, and probe; the page calls real `createService`, `updateService`, and `probeService` APIs. |
| Whisper filter | `GET http://127.0.0.1:5182/api/v1/services` exit 0, 0.013s; page filter inspection | **FAIL.** Live data has 8 services, 2 matched by `LOCAL_CAPABILITIES`; `local-whisper` / `本地 Whisper 对齐` has capability `speech_alignment`. `VoiceAlignmentPage.tsx` admits every `speech_alignment` service, so this Whisper-labelled service is rendered in 本地服务. This violates “Whisper 不得出现在本页或模型服务”. The direct test only excludes a `speech_recognition` Whisper fixture and does not cover this live case. |
| Real probe wiring | `POST http://127.0.0.1:5182/api/v1/services/local-indextts/probe` | PASS for real endpoint reachability: exit 0, HTTP 200, 0.009s. Returned `available:false`, `error_code:PROBE_ERROR`, `latency_ms:2`; this is an actual probe result, not a mocked success. |
| Full frontend test gate | `cd web-v2 && npm test` | PASS: exit 0, 24s; 20 files, 439 passed, 0 failed, 0 skipped. Existing React `act(...)` warnings were emitted by unrelated `CreateTaskPage` tests. |
| Build gate | `cd web-v2 && npm run build` | PASS: exit 0, 4s; TypeScript check and Vite build completed (70 modules). |
| 5182 current source / single instance | `curl http://127.0.0.1:5182/settings/voice-alignment`; `curl http://127.0.0.1:5182/src/pages/VoiceAlignmentPage.tsx`; `ps` / `ss` | PASS. Route HTTP 200; served module contains current 本地服务, filter, preview, and probe code and has the same 28,999-byte source ETag/mtime. Exactly one Vite listener is on 5182: PID 694579. |

## Failure location

`web-v2/src/pages/VoiceAlignmentPage.tsx`: `LOCAL_CAPABILITIES` includes `speech_alignment`, and `load()` uses only `LOCAL_CAPABILITIES.includes(s.capability)`. It must additionally exclude Whisper before this assignment can pass.
