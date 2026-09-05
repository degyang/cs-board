# WEB-LOCAL-003 — 本地服务 Whisper 排除回归修复

## 输入

`docs/workmates/receipts/WEB-LOCAL-002-V.md` — FAIL verdict: live `local-whisper` / `本地 Whisper 对齐` with `capability: 'speech_alignment'` and `adapter_type: 'whisper'` passed the `LOCAL_CAPABILITIES` filter because no structured exclusion existed.

## 改动

| 文件 | 变更 |
| --- | --- |
| `web-v2/src/pages/VoiceAlignmentPage.tsx` | Added `isWhisperService()` predicate matching `adapter_type === 'whisper'` or `service_id === 'local-whisper'`; applied it in `load()` filter alongside the capability check. |
| `web-v2/tests/voice-alignment-page.test.tsx` | Added regression test `'excludes Whisper from local services by adapter_type and service_id, not display name'` with live-shaped fixture (`service_id: 'local-whisper'`, `adapter_type: 'whisper'`, `capability: 'speech_alignment'`). |

No backend, service data, dynamic infographic, other page, or other ticket was modified.

## 命令与结果

| 命令 | 退出码 | 通过/失败/跳过 | 耗时 |
| --- | --- | --- | --- |
| `cd web-v2 && npx vitest run tests/voice-alignment-page.test.tsx` | 0 | 5 / 0 / 0 | 10.27s |
| `cd web-v2 && npm test` | 0 | 440 / 0 / 0 | 20.42s |
| `cd web-v2 && npm run build` | 0 | 70 modules, 1.19s | 1.19s |

## 验证逻辑

1. `isWhisperService(s)` checks `s.adapter_type === 'whisper' || s.service_id === 'local-whisper'` — structured fields only, no display-name or i18n text matching.
2. `load()` applies `LOCAL_CAPABILITIES.includes(s.capability) && !isWhisperService(s)`.
3. Regression test uses the exact live-data shape: `service_id: 'local-whisper'`, `adapter_type: 'whisper'`, `capability: 'speech_alignment'`, `display_name: '本地 Whisper 对齐'`. Asserts this service is absent while a normal `speech_alignment` service is present.
4. All existing assertions remain intact; no skip added; no commit or push performed.
