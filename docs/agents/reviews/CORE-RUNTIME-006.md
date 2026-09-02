# CORE-RUNTIME-006 Independent Review

Verdict: `APPROVED`

Reviewed delivery: `de57fab2e1e162021aeba78b5ea70de35ee7f89b` on
`fix/mountain-capability-secret-contract`; contract base:
`7ac3cb003327110d58c7d48cf75131d207018d5f`. The attempt-3 implementation is
`706ab2ef1d2b191f769577645b27077a8b921e83`.

## Scope review

`git diff --check 7ac3cb0...de57fab` passed. The cumulative task diff remains
within the authorised runtime/start boundary, zero-skip test migration, and
delivery-report surfaces. The attempt-3 delta (`eb1a248...de57fab`) is limited
to `scripts/run_mountain_backend.py`, the focused runtime test, and the report.
It replaces uvicorn's independent host/port bind with a launcher-owned socket,
requests graceful shutdown on `SIGTERM`, closes that socket in `finally`, and
adds a real sequential fresh-data-dir regression. No DTO, persistence, secret,
web-v2, media, or orchestration implementation surface changed.

## Independently reproduced gates

```text
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS timeout --signal=TERM --kill-after=5s \
  180s /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
exit 0; 457 passed, 0 skipped, 4 warnings, 3 subtests passed in 81.23s

/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_backend_runtime_17.py tests/test_mountain_server.py
exit 0; 35 passed in 32.50s

/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py
exit 0
```

The full-suite exit is pytest's normal zero exit, well inside the 180-second
hard cap; it was not a timeout or signal result. The focused suite includes
`test_two_fresh_data_dirs_reuse_same_port_after_normal_shutdown`: it starts two
real launcher children with different temporary data directories on one fixed
port, observes health and each child return code `0`, verifies each PID is
dead and directory is removable, then performs a plain immediate socket bind
before the next launch. It neither sleeps to mask reuse nor broad-matches and
kills processes.

The independent real-launcher smoke used fresh encrypted storage on port
`47305`, observed health `ok`, completed the real checker, successful
services/assets/settings reads and a structured unknown-route `404`, then
confirmed launcher PID `303760` terminated and deleted its temporary directory.
After all gates, process inspection found no pytest, `run_mountain_backend`,
or uvicorn process. This satisfies the launch, structured-error, cleanup, and
immediate same-port-rebind acceptance criteria.
