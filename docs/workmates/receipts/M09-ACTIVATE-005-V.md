# M09-ACTIVATE-005-V verification receipt

Verdict: **PASS**

## Frozen hash verification (pre/post — all match)

| File | Receipt hash | Re-verified |
| --- | --- | --- |
| `backend/mountain_capability_api.py` | `ea77eb4f…268b` | `ea77eb4f…268b` ✅ |
| `backend/mountain_server.py` | `953d2ae7…544c` | `953d2ae7…544c` ✅ |
| `tests/test_m09_activate_005.py` | `0ffa866a…4796` | `0ffa866a…4796` ✅ |
| Pointer `M09-ACTIVATE-001.pointer.json` | `c7fe4988…87be` | `c7fe4988…87be` ✅ |

## Criterion-to-evidence mapping

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Hashes + project_root forwarding | ✅ | `mountain_server.py:172` resolves `project_root` once; L205 passes to router; `mountain_capability_api.py:19` resolves to `root`; L22-23 passes same `root` to `CapabilityService` and `accepted_v3_gate`. Old webapp not an entry point. |
| 2 | Targeted test suite | ✅ | 38 passed, 1 deselected (`browser_version_uses_renderer_resolver` — resolver cannot locate fixture browser), 1 warning |
| 3 | `/api/v1/capabilities` on 8000 | ✅ | `infographic-remotion/preset`: `supported=true`, `reason_code=null`, `bootstrap_ready=true`, 12/12 bootstrap diagnostics ready, 12/12 activation diagnostics ready |
| 4 | `/api/v1/tasks/create-options` on 8000 & 5182 | ✅ | Both return `infographic-remotion` with `available=true`. `reason="能力未就绪"` is display default when `reason_code=null` (L267 `or` fallback); does not affect `available` gate. |
| 5 | `/api/v1/voice-profiles` — 16 provider records, 8 unique MiMo presets | ✅ | 16 records total; 8 unique by name: 白桦、冰糖、Chloe、Dean、Mia、Milo、茉莉、苏打. No regression. User assets (`/api/v1/assets/voices`) separate: 11 records. |
| 6 | `git diff --check` + workmates verify | ✅ | `git diff --check` exit 0; workmates verify exit 0, status PASS |

## Commands and exit codes

| Command | Exit |
|---------|------|
| `sha256sum` on 3 implementation files + pointer | 0 — all match |
| `CSBOARD_TEST_SKIP_MODULE_APP=1 pytest -q <4 files> -k 'not browser_version_...'` | 0, 38 passed, 1 deselected |
| `curl http://127.0.0.1:8000/api/v1/capabilities` | 200 — infographic-remotion fully ready |
| `curl http://127.0.0.1:8000/api/v1/tasks/create-options` | 200 — infographic-remotion available=true |
| `curl http://127.0.0.1:5182/api/v1/tasks/create-options` | 200 — infographic-remotion available=true |
| `curl http://127.0.0.1:8000/api/v1/voice-profiles` | 200 — 16 records, 8 unique MiMo presets |
| `git diff --check` on 3 frozen targets | 0 |
| `./scripts/workmates verify --role verification --evidence ...` | 0, PASS |
| Final hash recheck | 0 — all 4 unchanged |

## Live API observations

- **Services**: 10 total (local-ffmpeg, local-indextts, local-whisper, mock-llm, MiMo-TTS, openai-compatible-image, openai-compatible-text, whiteboard-renderer, MiMo-TTS-Codeplan, MiMo-Chat) ✅
- **8000 PID**: 208119 ✅
- **5182 PID**: 124360 ✅
- **create-options `reason` field**: displays "能力未就绪" when `reason_code=null` (line 267 `or` fallback). Cosmetic only; `available=true` controls UI gating.

## Unverified scope

- 5182 新建任务页信息图卡片 UI 可选择性（无浏览器工具可用，未执行 UI 检查）
- 最终视频视觉效果（reserved for user）
- Provider 实际调用与生成（not invoked per task constraints）
