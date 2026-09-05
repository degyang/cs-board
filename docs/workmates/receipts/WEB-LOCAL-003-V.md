# WEB-LOCAL-003 independent verification receipt

## Verdict: PASS

## Independent evidence

| Required check | Command / observation | Result |
| --- | --- | --- |
| Live Whisper shape | `GET http://127.0.0.1:5182/api/v1/services` | Exit 0. The 8-service response contains `{service_id:"local-whisper", adapter_type:"whisper", capability:"speech_alignment", display_name:"本地 Whisper 对齐"}`. |
| Structured exclusion | Source inspection and served-module inspection | PASS. `isWhisperService(s)` uses `s.adapter_type === 'whisper' || s.service_id === 'local-whisper'`; `load()` combines it with the capability predicate. No display-name text matching is used. |
| Normal alignment retained | `npx vitest run tests/voice-alignment-page.test.tsx` | Exit 0, 1 file / 5 passed / 0 failed / 0 skipped, 12s. The independent regression test uses the required live-shaped Whisper fixture and asserts it absent while normal `speech_alignment` service `local-align` remains visible. |
| Full frontend gate | `cd web-v2 && npm test` | Exit 0, 20 files / 440 passed / 0 failed / 0 skipped, 22s. Unrelated existing React warnings do not affect the exit status. |
| Production build | `cd web-v2 && npm run build` | Exit 0, TypeScript check passed; Vite built 70 modules, 5s wall time (Vite: 1.20s). |
| 5182 route/current module | `GET /settings/voice-alignment`; `GET /src/pages/VoiceAlignmentPage.tsx` | Both exit 0 / HTTP 200. Served module contains the current structured predicate and combined filter. Workspace module: 29,241 bytes; served ETag `W/"29241-1788600935226"`, matching its current mtime/size. |
| Single listener | `ss -ltnp '( sport = :5182 )'`; process listing | PASS. Exactly one Vite listener/process: PID **702514**, `node ./node_modules/vite/bin/vite.js --host 0.0.0.0 --port 5182 --strictPort --force`. |

No implementation, test gate, or service data was modified by this verification.
