# M09-RUNTIME-007-V verification receipt

Verdict: **PASS**

## Frozen hash verification (pre/post — no drift)

| File | Assignment hash | Pre-verify | Post-verify |
| --- | --- | --- | --- |
| `backend/mountain_server.py` | `85f65b47…ac078` | `85f65b47…ac078` ✅ | `85f65b47…ac078` ✅ |
| `csboard/adapters/filesystem/service_registry.py` | `fea4c1d4…b863` | `fea4c1d4…b863` ✅ | `fea4c1d4…b863` ✅ |
| `scripts/run_mountain_backend.py` | `6f547366…841d3` | `6f547366…841d3` ✅ | `6f547366…841d3` ✅ |
| `tests/test_m09_runtime_007.py` | `1f606345…1f3e` | `1f606345…1f3e` ✅ | `1f606345…1f3e` ✅ |

## Criterion-to-evidence mapping

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Pre/post hashes + code audit | ✅ | 4/4 match. Production opt-in at L320 (`CSBOARD_STARTUP_READINESS_PROBE=1`); tests offline by default (L95 `startup_readiness_probe=False`); deterministic single-candidate per prerequisite (L158 `probe_enabled_readiness_services`); root-partitioned cache at L120-137 (`str(self._data_dir)` key); failures cached as unavailable (L359-386), cannot abort startup. |
| 2 | Test suite | ✅ | 61 passed, 1 deselected (`browser_version_uses_renderer_resolver`, environment-specific) |
| 3 | 10-service topology + startup cache shape | ✅ | Health: `service_count=10`, `startup_readiness={enabled:true, probed:4, available:4}`. Same four-service accepted shape: Codeplan text + MiMo TTS speech + local Whisper + local FFmpeg. |
| 4 | PM restart evidence | ✅ | First FAIL: `SERVICE_PROBE_CHANGED` retained. Corrected PASS: zero manual POST, 5.253s, probed:4/available:4, service_count=10, supported=true, PID 292980, tmux %26. PM test evidence: 12 passed, exit 0. |
| 5 | Live 8000/5182 API | ✅ | Health: service_count=10, startup_readiness enabled/probed:4/available:4. Capabilities: supported=true, reason_code=null, bootstrap_ready=true. Create-options 8000 & 5182: available=true, no reason key. PID 8000=292980, 5182=124360. |
| 6 | git diff --check + workmates verify | ✅ | Both exit 0 |

## Commands and exit codes

| Command | Exit |
|---------|------|
| `sha256sum` on 4 frozen files (pre) | 0 — all match |
| `pytest <6 test files> -k 'not browser_version_...'` | 0, 61 passed, 1 deselected |
| `curl 8000 /api/v1/health` | 200 — service_count=10, startup_readiness enabled/4/4 |
| `curl 8000 /api/v1/capabilities` | 200 — supported=true, 12/12 diagnostics |
| `curl 8000 /api/v1/tasks/create-options` | 200 — available=true, no reason key |
| `curl 5182 /api/v1/tasks/create-options` | 200 — available=true, no reason key |
| `ss -tlnp \| grep :8000\|:5182` | PID 292980 / 124360 ✅ |
| `git diff --check` on 4 frozen targets | 0 |
| `./scripts/workmates verify --role verification --evidence ...` | 0, PASS |
| `sha256sum` on 4 frozen files (post) | 0 — unchanged |

## PM evidence cross-reference

| PM claim | Verified |
| --- | --- |
| First restart: broad probe → `supported=false / SERVICE_PROBE_CHANGED` | ✅ (in PM receipt) |
| Corrected restart: zero manual POST | ✅ |
| Startup 5.253s | ✅ |
| probed=4, available=4 | ✅ |
| service_count=10 | ✅ |
| supported=true, reason_code=null | ✅ |
| PID 292980, tmux %26 | ✅ (ss confirms) |
| PM test evidence: 12 passed, exit 0 | ✅ |

## Code audit summary

- **Production opt-in**: `CSBOARD_STARTUP_READINESS_PROBE=1` env var → `startup_readiness_probe=True` (L320). Tests default `False` (L95).
- **Deterministic single-candidate**: `probe_enabled_readiness_services()` selects one enabled service per `text_generation`, `speech_synthesis`, `speech_alignment`, `media`. No fallback probing on restart.
- **Root-partitioned cache**: `_root_probe_cache()` uses `str(self._data_dir)` as dict key. Interleaved registries cannot share probe results. Legacy flat-cache migration only for test injection seam.
- **Fail closed**: each candidate failure cached as unavailable result; cannot abort startup. Startup counts exposed via health check.

## Evidence path

`.workmates-evidence/M09-RUNTIME-007-V.json`
