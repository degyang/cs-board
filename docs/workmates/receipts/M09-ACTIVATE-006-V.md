# M09-ACTIVATE-006-V verification receipt

Verdict: **PASS**

## Frozen hash verification (pre/post — no drift)

| File | Assignment hash | Pre-verify | Post-verify |
| --- | --- | --- | --- |
| `csboard/application/commands.py` | `db452215…d19782` | `db452215…d19782` ✅ | `db452215…d19782` ✅ |
| `tests/test_m09_activate_006.py` | `8e3af1c9…8b51c` | `8e3af1c9…8b51c` ✅ | `8e3af1c9…8b51c` ✅ |

## Criterion-to-evidence mapping

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | Frozen hashes unchanged | ✅ | Pre & post both match assignment |
| 2 | Test suite | ✅ | 69 passed (8+36+25), 1 deselected (`browser_version_uses_renderer_resolver`, environment-specific) |
| 3 | supported=true → available=true, no `reason` | ✅ | 8000 create-options: `available=true`, `"reason" not in dict` |
| 4 | supported=false + reason → stable reason; missing/empty/non-string → CAPABILITY_NOT_AVAILABLE | ✅ | Covered by 8 passed in `test_m09_activate_006.py` (direct regression, no provider) |
| 5 | Live 8000 & 5182 create-options | ✅ | Both: `available=true`, reason key absent. Health: `service_count=10` |
| 6 | git diff --check + workmates verify | ✅ | Both exit 0 |

## Commands and exit codes

| Command | Exit |
|---------|------|
| `sha256sum` on 2 frozen files (pre) | 0 — match |
| `pytest tests/test_m09_activate_006.py tests/test_infographic_activation_projection.py` | 0, 8 passed |
| `pytest tests/test_capabilities_api.py tests/test_infographic_capability.py` | 0, 36 passed |
| `pytest tests/test_infographic_activation.py -k 'not browser_version_...'` | 0, 25 passed, 1 deselected |
| `curl 8000 /api/v1/capabilities` | 200 — supported=true, 12/12 diagnostics ready |
| `curl 8000 /api/v1/tasks/create-options` | 200 — available=true, no reason key |
| `curl 5182 /api/v1/tasks/create-options` | 200 — available=true, no reason key |
| `curl 8000 /api/v1/health` | 200 — service_count=10 |
| `git diff --check` | 0 |
| `./scripts/workmates verify --role verification --evidence ...` | 0, PASS |
| `sha256sum` on 2 frozen files (post) | 0 — unchanged |

## Evidence path

`.workmates-evidence/M09-ACTIVATE-006-V.json`
