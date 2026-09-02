# MEDIA-PREFLIGHT-004 Independent Review

Verdict: `CHANGES_REQUESTED`

Reviewed delivery `8532302a77b6acca3fad5e40078bf081b67f4296` on
`feat/mountain-media-work-orders`, against contract base
`6fc2924ee82442d49aa61dfe6c9893709f417832`. The implementation commit is
`d9f3a414ece4ae9320df618f8f28d9838aa24508`.

## Scope and passing evidence

`git diff --check 6fc2924...8532302` passed. The cumulative diff is limited to
the authorised preflight CLI, focused tests, and delivery report; it does not
touch the Stage chain, backend DTOs, web UI, or media-generation paths. The
report secret/absolute-path scan passed.

Independent reproduction using
`/mnt/d/workstation/projects/cs-board/.venv/bin/python` found:

```text
python -m pytest -q tests/test_media_preflight.py
exit 0; 5 passed in 2.65s

python scripts/validate_skill_contracts.py
exit 0; Skill contract validation passed

python scripts/check_media_preflight.py --json
exit 1 (environment readiness, not detector failure): ffmpeg=VERSION_FAILED,
ffprobe=VERSION_FAILED, IndexTTS=HTTP_TIMEOUT, Whisper model absent; node,
entries, and temporary-artifact cleanup ready
```

The live JSON was stable and sanitized. It records the expected non-ready
environment without starting a service or generating media. The ready-path
test uses real local version subprocesses and a controlled HTTP server; the
temporary artifact assertions show an empty probe directory after both normal
and injected-failure paths.

## Required corrections

1. Acceptance 3 and 5 require controlled HTTP `4xx` and `5xx` evidence. The
   focused suite only asserts `HTTP_503`; it has no controlled `4xx` case.
   Add a real local-server `4xx` test that asserts a distinct fail-closed
   reason code and nonzero CLI readiness.
2. The delivery report says the full suite had a normal zero exit, but that
   could not be reproduced in the declared owner worktree. After focused
   checks and the live probe, an independent `python -m pytest -q` remained
   running beyond 130 seconds; it was stopped by the reviewer, so it is not
   normal-exit evidence. Re-run it with the bounded command below, diagnose
   and correct any delivery-relevant regression or accurately amend the
   report. Do not count a watchdog signal/timeout as success.

## Bounded next scope and reproduction

Limit the correction to `scripts/check_media_preflight.py`,
`tests/test_media_preflight.py`, and
`docs/agents/reports/MEDIA-PREFLIGHT-004.md`. Do not change Worker pipeline,
Work Order, DTO, web, or media-generation implementation.

```bash
cd /mnt/d/workstation/projects/cs-board-media
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_media_preflight.py
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/validate_skill_contracts.py
/mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/check_media_preflight.py --json
env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS timeout --signal=TERM --kill-after=5s 180s \
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
git diff --check 6fc2924...HEAD
! rg -n 'Authorization|api[_-]?key\s*[:=]\s*[^[:space:]]{8}|/home/|/mnt/|/tmp/' \
  docs/agents/reports/MEDIA-PREFLIGHT-004.md
```

The live preflight may retain its nonzero environment-readiness exit, with its
reason codes recorded verbatim. Focused tests, skill validation, full suite,
diff check, and report scan must exit zero; the full suite must finish before
the 180-second cap without timeout or signal. `MEDIA-E2E-003` remains blocked
on full live readiness and an approved review.
