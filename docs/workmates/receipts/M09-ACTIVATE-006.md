# M09-ACTIVATE-006 backend receipt

Status: `READY_FOR_VERIFY`

## Delivered scope

- `create_options()` now omits `reason` when the native capability projection
  reports `supported=true`, matching the existing available-option convention.
- Closed projections retain a non-empty stable reason code; missing, empty, or
  non-string reason codes fail closed as `CAPABILITY_NOT_AVAILABLE`.
- Added direct no-provider/no-task regression coverage for open, closed with a
  reason, and closed without a valid reason.

## Verification

| Command | Exit | Result |
| --- | ---: | --- |
| `CSBOARD_TEST_SKIP_MODULE_APP=1 .venv/bin/python -m pytest -q tests/test_m09_activate_006.py tests/test_infographic_activation_projection.py` | 0 | 8 passed |
| `CSBOARD_TEST_SKIP_MODULE_APP=1 .venv/bin/python -m pytest -q tests/test_capabilities_api.py tests/test_infographic_capability.py` | 0 | 36 passed |
| `CSBOARD_TEST_SKIP_MODULE_APP=1 .venv/bin/python -m pytest -q tests/test_infographic_activation.py -k 'not browser_version_uses_renderer_resolver'` | 0 | 25 passed, 1 deselected |
| `git diff --check` | 0 | clean |

The deselected resolver test is environment-specific and unrelated to the
create-options projection. No Task, render, provider, pointer, fingerprint,
service configuration, secret, frozen output, or frontend was changed.

## File hashes (SHA-256)

| File | SHA-256 |
| --- | --- |
| `csboard/application/commands.py` | `db452215848e2d840f64b0a4bfb1314e1bd28b6c8ef9e51a1236586200d19782` |
| `tests/test_m09_activate_006.py` | `8e3af1c9c778bbd651d877d2fcef7fcb2a0eea1a5956016c992fb604d6f8b51c` |

No commit, merge, or push was performed. Backend client remains idle for PM
integration and independent verification.
