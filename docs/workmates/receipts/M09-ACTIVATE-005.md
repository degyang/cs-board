# M09-ACTIVATE-005 backend receipt

Status: `READY_FOR_VERIFY`

## Scope delivered

- Native capability router now requires an explicit `project_root`, resolves it once,
  and supplies that same root to `CapabilityService` and `accepted_v3_gate`.
- Native composition root forwards its already-computed `project_root` to the router.
- Direct regression coverage uses separate runtime-data and project-root directories,
  checks root normalization and forwarding, and verifies missing/malformed pointers
  close the external gate.

## Verification

| Command | Exit | Result |
| --- | ---: | --- |
| `CSBOARD_TEST_SKIP_MODULE_APP=1 .venv/bin/python -m pytest -q tests/test_m09_activate_005.py tests/test_capabilities_api.py tests/test_infographic_activation_projection.py tests/test_infographic_activation.py -k 'not browser_version_uses_renderer_resolver'` | 0 | 38 passed, 1 deselected |
| `git diff --check` | 0 | clean |

The deselected browser-resolver test is unrelated to this wiring: in this
environment its resolver command cannot locate the fixture browser. The passed
activation-projection set includes the direct `create_options()` activation
projection regression.

## File hashes (SHA-256)

| File | SHA-256 |
| --- | --- |
| `backend/mountain_capability_api.py` | `ea77eb4f799e812dba8748ceb3b7667bbf93fceaf8624b69b2432ff03fd4268b` |
| `backend/mountain_server.py` | `953d2ae76931637a7eb5fe9bef8459ccaf612f69b7698d5b7762f25050bf544c` |
| `tests/test_m09_activate_005.py` | `0ffa866a19399a19e4af6ac37d9085d2a00bc9dd677decd65d201d18773e4796` |

No task/render creation or provider invocation was performed. No commit, merge,
push, service setting, secret, pointer, frozen output, frontend, or board change
was made.
