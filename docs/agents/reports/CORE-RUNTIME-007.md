# CORE-RUNTIME-007 report

## Delivery state

Bounded runtime diagnosis and lifecycle recovery are complete on the registered
branch `feat/mountain-assets-settings-backend`.  The shared runtime blocker is
resolved: the full pytest suite now exits normally without an outer watchdog.
This task cannot be marked `REVIEW_READY`, because the contract's no-skips and
base-range diff gates are not satisfied by pre-existing, out-of-scope changes.

## Diagnosis and recovery

The isolated reported boundary passed (`1 passed in 3.17s`), but a bounded full
diagnostic stalled immediately after `test_smoke_checker_success_path` had
launched and then lost its test-owned `run_mountain_backend.py` child.  The
parent pytest process remained blocked after that child was gone.  The current
registered branch had regressed the lifecycle implementation present at the
contract base: it preflight-bound and closed a socket, then used ordinary
`uvicorn.run`, and it had removed the immediate same-port reuse regression.

`scripts/run_mountain_backend.py` now owns a `SO_REUSEADDR`/`SO_LINGER`
listener for the whole Uvicorn lifecycle, handles SIGTERM by requesting a
graceful server shutdown, and closes the listener in `finally`.
`tests/test_backend_runtime_17.py` restores the focused two-fresh-data-dir,
same-port lifecycle regression.  No media-preflight behavior changed.

Focused recovery evidence:

```text
tests/test_backend_runtime_17.py::test_two_fresh_data_dirs_reuse_same_port_after_normal_shutdown
tests/test_backend_runtime_17.py::test_smoke_checker_success_path
tests/test_mountain_server.py::test_inputs_and_start_boundary
3 passed in 14.19s
```

No test-owned `pytest` or `run_mountain_backend.py` process remained after the
full runs.  A separately owned backend on port 8765 was observed and left
untouched.

## Required gates

| Command | Exit | Result |
| --- | ---: | --- |
| `/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q` | 0 | `506 passed, 5 skipped, 4 warnings, 3 subtests passed in 95.95s` |
| `/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q -rs` | 0 | Same normal exit; skips are four deprecated `segment_script` legacy tests in `tests/test_mountain_api.py` and `tests/test_port_conformance.py:63` (`httpx not installed`). |
| `git diff --check de57fab...HEAD` | 2 | Fails before this task's changes on trailing whitespace in `docs/Mountain/25-ccb-execution-plan-final-correction.md` (lines 3-7) and `docs/Mountain/27-ccb-execution-plan-recovery.md` (lines 3-5). Those files are outside allowed surfaces. |

## Handoff

`MEDIA-PREFLIGHT-004`'s runtime-timeout blocker is resolved, but it should not
be resumed from this report: CORE-RUNTIME-007's contract still lacks a
no-skips full-suite result and a passing required diff gate.  This report does
not approve, dispatch, or alter MEDIA task status.
