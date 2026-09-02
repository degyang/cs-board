# MEDIA-PREFLIGHT-004 delivery report

- Status: REVIEW_READY
- Implementation commit: recorded below after commit
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
