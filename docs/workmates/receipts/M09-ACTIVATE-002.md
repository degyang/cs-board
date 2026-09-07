# M09-ACTIVATE-002 — backend receipt

Verdict: **READY_FOR_VERIFY**

## Scope delivered

- `_get_probe_timeout()` now constructs a compatible `httpx.Timeout` with all
  four explicitly bounded values: connect 2 seconds, read/write 5 seconds, and
  pool 2 seconds.
- Added offline regressions that prove construction succeeds and every timeout
  value is finite and positive. A mocked IndexTTS HTTP client returns a local
  200 response; the registry result is available with no `PROBE_ERROR`.
- No service definition, secret, activation pointer, capability policy,
  renderer, output, frontend, assignment, or board was changed. No provider or
  service was started or called.

## Checks

| Command | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q tests/test_service_registry.py tests/test_mountain_service_api.py` | exit 0; 44 passed, 1 warning |
| `.venv/bin/python -m pytest -q tests/test_capabilities_api.py` | exit 0; 6 passed |
| `git diff --check -- csboard/adapters/filesystem/service_registry.py tests/test_service_registry.py` | exit 0 |
| `/mnt/d/workstation/projects/cs-board/scripts/workmates verify --role verification --evidence /tmp/m09-activate-002-workmates-evidence.json` | exit 0; PASS; runtime guard ran 12 tests (integration-worktree guard only, not a substitute for this worker diff's focused tests) |

## Frozen worker state

- Base commit: `e34ba6e83ef1a6c3ec3ad5274485505379ce0a21`
- Scoped implementation/test diff SHA-256: `883e7d047a013ecbd817691e70cf670e5cf26c3a42717026207424c61ab1adf5`
- `csboard/adapters/filesystem/service_registry.py` SHA-256: `0ed986c938e53fef78d4cf43491bd32de9c982c2897043c8989f5c7e221739b2`
- `tests/test_service_registry.py` SHA-256: `5f662827d220fa1cf0280403fb8e5eee10a8e9b84085112d7355fe5265ef54a8`

Independent verification and PM integration/restart with real probes remain
outside this task.
