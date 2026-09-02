# CORE-RUNTIME-006 Delivery Report

Status: `BLOCKED`

Base: `7ac3cb003327110d58c7d48cf75131d207018d5f`.

## Runtime defect fixed

- Implementation commit: `264425228f77508521fe42dfa14ca0f5c4a8b469`
  (`fix(mountain): fail closed before pipeline startup`).
- Changed files: `csboard/application/commands.py` and
  `csboard/application/service_resolver.py`.
- Reproduction: `tests/test_mountain_server.py::test_inputs_and_start_boundary`
  created a fresh app, saved valid inputs, and called run start. Seeded service
  definitions existed but their required secrets were unavailable. `start_run`
  treated mere service selection as readiness, entered the pipeline, and hung
  instead of returning its asserted `400 CAPABILITY_NOT_AVAILABLE`.
- Fix: the start boundary now checks the existing value-free registry
  availability contract for every resolved stage service. Missing required
  credentials become the existing structured capability error before an adapter
  or pipeline can start. No secret value is read into a response or log.

## Gates

```text
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS timeout --signal=TERM --kill-after=5s 180s \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
exit 0 in 76.32s
451 passed, 5 skipped, 4 warnings, 3 subtests passed
```

The initial required full-suite run reached the watchdog at exit `124` after
180 seconds, with four skips already printed. After the fail-closed fix, the
same command exited normally and no longer hung. It cannot satisfy acceptance
item 1 because the contract requires `0 skipped`.

```text
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_backend_runtime_17.py tests/test_mountain_server.py
exit 0
34 passed in 29.13s

/mnt/d/workstation/projects/cs-board/.venv/bin/python \
  scripts/smoke_real_backend_contract.py
exit 0
```

The smoke used a fresh encrypted data directory and a real launcher on port
48613. It observed health `ok`, then successful representative reads:
`/services`, `/assets/styles?kind=preset`, `/settings/toolchain`,
`/settings/storage`, `/settings/diagnostics`, and a structured 404 for the
unknown API path. The checker passed. Cleanup proved launcher PID `248381`
exited and the temporary directory was deleted.

```text
git diff --check 7ac3cb0...HEAD
exit 0
```

## Blocking evidence

The five remaining skips are not caused by the runtime change and cannot be
removed or hidden within this contract's permitted surfaces:

- Four class-level skips in `tests/test_mountain_api.py` (lines 123, 137, 188,
  and 206): `Legacy mountain_api tests — segment_script alias removed, legacy
  API being decommissioned`.
- One skip in `tests/test_port_conformance.py:63`: `httpx not installed`.

Focused evidence command:

```text
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q -rs \
  tests/test_mountain_api.py tests/test_secret_store.py \
  tests/test_secret_security.py tests/test_input_transaction_11.py
51 passed, 4 skipped in 13.62s

/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q -rs \
  tests/test_port_conformance.py
9 passed, 1 skipped in 0.49s
```

Therefore this is not REVIEW_READY. The branch must remain `BLOCKED` until the
task owner authorizes a zero-skip full-suite baseline or an in-scope resolution
for the legacy/environment skips. At report commit and push, the worktree is
clean.

## Attempt 2 recovery — REVIEW_READY

Recovery implementation commit: `4ab3867365068bc977ea1e330a5c7ce734e35212`
(`test(mountain): restore executable zero-skip boundaries`). The recovery uses
only the two test files explicitly authorized by the amended contract:

- The four formerly class-skipped legacy stage assertions in
  `tests/test_mountain_api.py` are now executable current `/api/v1` boundary
  tests. They cover structured NotFound for an unknown task/run, and the real
  stage/pipeline response for missing inputs (`ok: false` with a nested
  `VALIDATION_ERROR`), without invoking a removed legacy route.
- `tests/test_port_conformance.py` now constructs the existing
  `OpenAITextAdapter` with its actual required `base_url` and asserts its
  `TextModelPort` conformance. It no longer masks the stale
  `OpenAICompatibleTextAdapter` class name as a missing-`httpx` skip.

All gates were rerun in this attempt and exited normally:

```text
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_mountain_api.py tests/test_port_conformance.py
23 passed in 2.26s

env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS timeout --signal=TERM --kill-after=5s 180s \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
exit 0 in 77.98s
456 passed, 4 warnings, 3 subtests passed

/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_backend_runtime_17.py tests/test_mountain_server.py
34 passed in 29.11s

/mnt/d/workstation/projects/cs-board/.venv/bin/python \
  scripts/smoke_real_backend_contract.py
exit 0
```

The real-launcher smoke used a fresh encrypted data directory and port 46917.
It observed health `ok`; successful reads for tasks, services, capabilities,
settings, and assets via the contract checker/smoke table; and structured 404
for an unknown API route. It confirmed launcher PID `264112` exited and deleted
its temporary directory `/tmp/csboard-smoke-0vy3f_6h`. No launcher, uvicorn, or
test child was left by the gate.

```text
git diff --check 7ac3cb0...HEAD
exit 0
```

All acceptance criteria now hold: the suite exits under 180 seconds with zero
failures and zero skips; the cold-launch/API/error/cleanup checks pass; and the
previous hang root cause remains covered by the focused runtime suite. The
worktree is clean after this report's delivery commit.

## Attempt 3 lifecycle correction — REVIEW_READY

Review correction commit: `706ab2ef1d2b191f769577645b27077a8b921e83`
(`fix(runtime): release launcher port on shutdown`).

The independent review reproduced a successful smoke whose process and
directory were gone, but a plain immediate bind on its port still raised
`EADDRINUSE`. The launcher now owns its listening socket, enables immediate
reuse/abortive-close semantics before passing it to uvicorn, and maps SIGTERM
to a graceful `Server.should_exit` request. It uses `Server._serve` directly
so this installed uvicorn version does not re-raise SIGTERM after graceful
shutdown and convert a normal launcher stop into child exit `-15`.

`tests/test_backend_runtime_17.py` now has a real sequential regression: two
different fresh data directories start the actual launcher on one fixed port.
For each round it checks health, the actual child return code is `0`, its PID
is dead, the directory is deleted, and a plain socket bind succeeds immediately
before the next round. No sleep, timeout-success condition, or broad process
matching is used.

All contractual gates were rerun in this attempt:

```text
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS timeout --signal=TERM --kill-after=5s \
  180s /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
exit 0 in 82.47s
457 passed, 4 warnings, 3 subtests passed

/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_backend_runtime_17.py tests/test_mountain_server.py
35 passed in 32.35s

/mnt/d/workstation/projects/cs-board/.venv/bin/python \
  scripts/smoke_real_backend_contract.py
exit 0
```

The real smoke used fresh encrypted storage on port 45979, reached health
`ok`, completed the services/assets/settings checks and structured unknown-route
404, and confirmed PID `290258` exited with its temporary directory deleted.

```text
git diff --check 7ac3cb0...HEAD
exit 0
```

The branch is clean after this report's delivery commit. This completes the
attempt-3 bounded correction and restores `REVIEW_READY`.
