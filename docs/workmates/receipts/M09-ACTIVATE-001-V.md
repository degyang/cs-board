# M09-ACTIVATE-001-V — verification receipt

Verdict: **BLOCKED**

## Reason

Implementation code passes all focused tests and the14-file SHA-256 binding is fully consistent. However, real integration on8000/5182 cannot open `infographic-remotion` because two independent prerequisites remain unresolved:

1. **No operator pointer in integration area** — `docs/workmates/receipts/M09-ACTIVATE-001.pointer.json` does not exist. The activation verifier projects this as `EVIDENCE_MISSING`. The pointer exists in the backend worktree (`/mnt/d/Workstation/Projects/cs-board-worktrees/backend/docs/workmates/receipts/M09-ACTIVATE-001.pointer.json`) but has not been copied/issued to the integration area.

2. **Bootstrap prerequisites not ready** — `bootstrap_ready: false` with reason `SERVICE_SECRET_MISSING`. Three service categories block bootstrap:
   - `service-text_generation` — `SERVICE_SECRET_MISSING` (openai-compatible-text: no api_key)
   - `service-speech_synthesis` — `SERVICE_PROBE_FAILED` (local-indextts: PROBE_ERROR; MiMo-TTS/MiMo-TTS-Codeplan: OPENAI_PROBE_ERROR)
   - `service-image_generation` — `SERVICE_SECRET_MISSING` (openai-compatible-image: no api_key)
   - `external-stage-gate` — `EXTERNAL_STAGE_BLOCKED` (consequence of the above)

   Per AGENTS.md: "seed 只补缺失 ID，禁止覆盖、删除、重命名或替换用户服务。" The missing secrets are user-owned configuration, not code defects.

## Circular dependency analysis (service_fingerprint ↔ pointer)

The task asked to specifically audit whether the `external_stage_gate` → `accepted_v3_gate(root)` → pointer → `service_fingerprint(bootstrap_diagnostics)` cycle prevents issuing a stable pointer.

**Finding: No blocking cycle.** The `_service_fingerprint` method at `csboard/application/capabilities.py:180` hashes both service identity records AND the current `diagnostics` list (which includes external-stage-gate readiness). However:

- The pointer's `service_fingerprint` is an immutable snapshot computed at pointer-creation time.
- When PM issues the pointer, external-stage-gate IS ready (pointer exists), so the fingerprint is computed in that state.
- At verification time, the verifier compares `current_service_fingerprint` against the pointer's stored value. If they match, activation opens; if not, it closes.
- A pointer created while external-stage-gate was ready will have a different fingerprint than one computed when it's not ready — this is by design, not a bug.

The pointer CAN be stably issued once bootstrap prerequisites are met. The fingerprint will be deterministic for a given service+diagnostics state.

## SHA-256 verification (14 files)

All14 files match the implementation receipt exactly:

| File | SHA-256 | Match |
| --- | --- | --- |
| `csboard/application/activation.py` | `34bffe07...` | ✅ |
| `csboard/application/capabilities.py` | `55a4bd78...` | ✅ |
| `csboard/application/commands.py` | `75bbec82...` | ✅ |
| `csboard/runtime/toolchain.py` | `d6e4bb63...` | ✅ |
| `cli/csboard.py` | `79558633...` | ✅ |
| `webapp/mountain_capability_api.py` | `e16608ab...` | ✅ |
| `webapp/mountain_server.py` | `972e764a...` | ✅ |
| `tests/infographic_activation_fixture.py` | `ddfed65d...` | ✅ |
| `tests/test_infographic_activation.py` | `53c364cb...` | ✅ |
| `tests/test_infographic_activation_projection.py` | `b01399d4...` | ✅ |
| `tests/test_infographic_capability.py` | `3cc87c8f...` | ✅ |
| `tests/test_cli_capabilities.py` | `7f4bb7d9...` | ✅ |
| `tests/test_toolchain_resolver.py` | `b86499e3...` | ✅ |
| `docs/workmates/receipts/M09-ACTIVATE-001.pointer.json` | (not in integration area) | N/A |

V3 receipt SHA-256: `8f5f5a675275791d3fc34fec4cccf402b7ff5ac5f50f89c9c50135526920991e` ✅

## Review corrections verification

| Correction | Status |
| --- | --- |
| `REAL_SMOKE_EVIDENCE_REQUIRED` constant restored | ✅ `capabilities.py:47` |
| CLI `webapp.*` guard restored | ✅ `test_cli_capabilities.py:56-69` |
| Old assertions preserved, new activation tests added | ✅ |
| Unmocked `CapabilityService` fixture (projection + fail-closed) | ✅ `test_infographic_activation_projection.py:112` |
| Final SHA-256 consistent | ✅ all14 match |

## Checks

| Command | Result |
| --- | --- |
| `pytest tests/test_infographic_activation.py tests/test_infographic_activation_projection.py tests/test_infographic_capability.py tests/test_infographic_task_creation.py tests/test_capabilities_api.py tests/test_cli_capabilities.py tests/test_infographic_routing_p4.py tests/test_toolchain_resolver.py` | exit 0; 88 passed |
| `git diff --check -- <M09 activation paths>` | exit 0 |
| `./scripts/workmates verify --role verification --evidence /tmp/m09-activate-001-v-evidence-1788747775.json` | exit 0; PASS |

## Real API state (8000/5182)

| Endpoint | State |
| --- | --- |
| `/api/v1/health` | ok, 9 services |
| `/api/v1/services` |9 services; local-ffmpeg/whisper/whiteboard-renderer available; local-indextts PROBE_ERROR; MiMo-TTS/Codeplan OPENAI_PROBE_ERROR; mock/text/image SECRET_NOT_CONFIGURED |
| `/api/v1/voice-profiles` | 16 provider records, 8 unique names (白桦/冰糖/Chloe/Dean/Mia/Milo/茉莉/苏打) |
| `/api/v1/capabilities` | infographic-remotion/preset: `supported: false`, reason `READINESS_FAILED`; whiteboard: `supported: false`, reason `CAPABILITY_NOT_AVAILABLE` |
| `/api/v1/tasks/create-options` | infographic-remotion: `available: false`, reason `READINESS_FAILED` |
| 5182 create-options | Matches8000 projection exactly |

## Next action (narrowest responsible party)

1. **PM**: Issue operator pointer to `docs/workmates/receipts/M09-ACTIVATE-001.pointer.json` from the backend worktree's pointer once bootstrap prerequisites are resolved.
2. **PM / User**: Configure missing service secrets (text_generation api_key, image_generation api_key) or accept that these services remain unavailable. speech_synthesis probe failures (local-indextts, MiMo-TTS) require running service instances, not code changes.
3. Once pointer is issued and bootstrap_ready becomes true, re-run verification to confirm real integration opens.

## Not verified

- Visual/video acceptance (no renderer ran)
- Canonical task/run creation (not permitted by this task)
- Backend worktree pointer.json content validity against current integration state (pointer was created for backend worktree context, not integration area)
