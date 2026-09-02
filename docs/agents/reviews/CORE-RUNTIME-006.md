# CORE-RUNTIME-006 Independent Review

Verdict: `CHANGES_REQUESTED`

Reviewed delivery: `eb1a248349f6213aded3dd74c5d15ad744a56e2a` on
`fix/mountain-capability-secret-contract`; contract base:
`7ac3cb003327110d58c7d48cf75131d207018d5f`.

## Scope review

The delivery diff is limited to the authorised runtime/start-boundary repair,
the two explicitly authorised zero-skip test migrations, and its delivery
report. `git diff --check 7ac3cb0...eb1a248` passed. The earlier production
repair makes `start_run` reject a resolved service with missing required
credentials before adapter/pipeline execution; the focused server boundary
test exercises the existing structured `CAPABILITY_NOT_AVAILABLE` response.
No DTO, persistence, secret, web-v2, media, or orchestration surface changed.

## Independently reproduced passing gates

```text
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS timeout --signal=TERM --kill-after=5s 180s \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
exit 0; 456 passed, 0 skipped, 4 warnings, 3 subtests passed in 81.21s

/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_backend_runtime_17.py tests/test_mountain_server.py
exit 0; 34 passed in 30.48s

/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py
exit 0
```

The real-launcher smoke used a fresh encrypted directory and observed health
`ok`; successful services, assets, settings reads; a structured unknown-route
404; then confirmed its launcher PID exited and its temporary directory was
deleted. The focused suite also covers occupied-port non-zero termination,
startup failure cleanup, checker failure cleanup/redaction, and structured
NotFound/error boundaries. No `run_mountain_backend` or uvicorn process was
present after the smoke.

## Required correction

Acceptance item 5 is not met: a launcher that reports its child terminated
does **not** make its test port immediately reusable. This also prevents two
successive fresh-data-dir cold starts on the same port.

Exact independent reproduction (on this delivery):

```text
/mnt/d/workstation/projects/cs-board/.venv/bin/python \
  scripts/smoke_real_backend_contract.py --port 48961
# exit 0; PID 280110 terminated and its temp directory was deleted

/mnt/d/workstation/projects/cs-board/.venv/bin/python \
  scripts/smoke_real_backend_contract.py --port 48961
# exit 1: "错误: 端口 48961 不可用" / launcher exited prematurely with code 1

python -c "import socket; s=socket.socket(); s.bind(('127.0.0.1',48961))"
# OSError: [Errno 98] Address already in use
```

At reproduction time `ss` showed no listener and process inspection found no
launcher/uvicorn child, so this is a socket-reuse/lifecycle failure rather
than a stale-process-name match. The current focused tests prove PID and
directory cleanup, but do not assert immediate same-port rebind after a
successful real launch.

Bounded next scope: make the real launcher/server shutdown release the bound
port for immediate reuse (without broad process matching), add a real
same-port sequential fresh-data-dir test that observes both child return codes
and immediate bind, then rerun the four contract gates above. Do not weaken
the bind assertion, add sleeps, or use timeout/signal termination as success.
