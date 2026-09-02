# MEDIA-PREFLIGHT-004 delivery report

- Status: BLOCKED
- Implementation commit: `d9f3a414ece4ae9320df618f8f28d9838aa24508`
- Branch: `feat/mountain-media-work-orders` (pushed with delivery commit)
- Scope: fail-closed, no-payload media dependency preflight only. No Stage Work Order or stage chain was run.

## Changed behavior

- Added `scripts/check_media_preflight.py`: stable, sanitized JSON CLI that performs bounded executable version probes; verifies renderer and Whisper entry files; reads enabled persistent service definitions; makes no-payload GET health/metadata probes; checks configured models; and proves atomic temporary write/readback/cleanup.
- Added `tests/test_media_preflight.py`: real executable subprocesses, controlled HTTP success/4xx/silent/malformed responses, model absence, injected artifact failure, cleanup, and child normal-exit evidence.
- Runtime evidence was written to ignored `.webapp/media-preflight.json`; it contains no credentials, source material, or absolute paths.

## Gates

| Command | Exit | Result |
| --- | --- | --- |
| `$PYTHON -m pytest -q tests/test_media_preflight.py` | 0 | 5 passed; no skip |
| `$PYTHON scripts/check_media_preflight.py --json` | 1 | Expected live readiness failure; reason codes below |
| `$PYTHON -m pytest -q` | 0 | Normal exit; no skips reported |
| `git diff --check 6fc2924...HEAD` | 0 | Clean |
| report secret/path scan | 0 | No matching secret or absolute-path pattern |

## Live readiness evidence

The live detector exited 1, which is an environment readiness result rather than a detector failure. JSON reported: `ffmpeg=VERSION_FAILED`, `ffprobe=VERSION_FAILED`, `node=ready` (`v24.20.0`), `renderer_entry=ready`, `whisper_alignment_entry=ready`, `temp_artifact=ready`, `indextts=HTTP_TIMEOUT`, and `whisper_model=MODEL_PATH_NOT_FOUND`.

No service was started or stopped. The temporary artifact check cleaned its workspace, and no preflight HTTP, Node, or Python child process remains after the probes.

## Known gap

Live media readiness is not green. In particular, the configured local IndexTTS endpoint did not respond, the local Whisper model is absent, and the resolved FFmpeg/ffprobe version commands returned nonzero. `MEDIA-E2E-003` must remain undispatched until a fresh live preflight is fully ready.

## Attempt 2 correction and gate evidence

- Added an independent real controlled-server HTTP 404 case. It asserts the
  distinct `HTTP_404` reason code and a nonzero CLI exit, alongside the
  existing HTTP 503 coverage.
- Focused preflight gate: exit 0; `6 passed` with no skips.
- Skill-contract validation: exit 0.
- Live preflight: exit 1, as an environment-readiness result. The observed
  reason codes were `VERSION_FAILED` (FFmpeg and ffprobe), `HTTP_TIMEOUT`
  (IndexTTS), and `MODEL_PATH_NOT_FOUND` (Whisper model); Node, both entries,
  and temporary-artifact cleanup were ready.
- Full-suite gate was run with the required 180-second TERM/KILL cleanup-only
  watchdog and exited 124. It was still executing
  `test_inputs_and_start_boundary` at 50% when the watchdog ended it. This is
  not normal-exit evidence and prevents `REVIEW_READY`; the watchdog was not
  used as a passing result. No preflight HTTP, Node, or Python child remained
  after cleanup.

The correction is limited to the preflight focused test and this report. The
full-suite timeout is outside this task's permitted change surfaces and needs
PM direction before any broader diagnosis or fix.

## Attempt 2 fresh worker reproduction

The dispatched correction was re-run in the registered MEDIA worktree. The
focused preflight suite exited 0 with `6 passed`, and skill-contract validation
exited 0. Live preflight exited 1 as the expected environment-readiness result:
FFmpeg and ffprobe reported `VERSION_FAILED`, IndexTTS reported `HTTP_TIMEOUT`,
and the Whisper model reported `MODEL_PATH_NOT_FOUND`; Node, both entries, and
temporary-artifact cleanup were ready.

The required full suite was run under its cleanup-only 180-second watchdog and
again exited 124 rather than normally. It therefore remains non-passing
evidence and this task remains `BLOCKED`, not `REVIEW_READY`. `git diff --check
6fc2924...HEAD` and the report secret/path scan both exited 0. No preflight
HTTP, Node, or Python process remained after the run.
