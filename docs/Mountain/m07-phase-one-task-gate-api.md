# Phase-one Task Gate API

The authoritative manual path is the six `CANONICAL_STAGES` order.  Gates are independent of StageStatus: `not-ready → waiting-review → approved|rejected|redo-required`.

- `GET /api/v1/tasks/{task_id}/runs/{run_id}/gates` returns all six gates in canonical order.
- `GET /api/v1/tasks/{task_id}/runs/{run_id}/stages/{stage}/gate` returns one gate.
- `POST /api/v1/tasks/{task_id}/runs/{run_id}/stages/{stage}/gate` accepts `{ "decision": "approve|reject|redo", "actor": "reviewer", "note": "optional", "evidence": [{"logical_key":"…","sha256":"…"}] }`.

A Gate response includes task/run/trace IDs, stage ID, status, decision, actor, decided time, attempt, revision and evidence. Unknown stages and malformed decisions return `400 body.error`; a conflicting decision returns `409 body.error`. Repeating the same decision with the same evidence is idempotent.

Before a Stage is run, every upstream gate must be approved. Otherwise the run endpoint returns `409 STAGE_GATE_REQUIRED` without executing the Stage. A completed Stage is placed in `waiting-review`; it is never automatically approved. Gate records live in `runs/{run_id}/gates.json`, are atomically replaced under the task lock, and are accompanied by redacted Event/Audit records. Notes are intentionally not copied to telemetry.

For `generate-illustrations`, candidate import is not approval: CCF must provide selected Codex image-generation candidate logical keys and hashes when the dedicated candidate-import contract is connected. No real image generation is triggered by this API.

## Stage entry truth

`POST /tasks/{task_id}/runs/{run_id}/start` first validates the Task/Run relation and persisted inputs. A valid input has a non-empty script (at least ten characters) and a non-empty reference audio file addressed by a safe `inputs/...` relative path. Missing Task/Run is `404 NOT_FOUND`; invalid inputs are `400 VALIDATION_ERROR` with safe `invalid_fields`. Success is side-effect-free and returns `waiting-manual-trigger`, the next stage and gates.

A single Stage response always has one authoritative envelope: `ok`, task/run/trace IDs, `stage`, `stages_executed`, `results`, `next_stage`, and `next_action`. A succeeded or skipped Stage may return `GATE_REVIEW_REQUIRED` only after all output Artifacts validate and its Gate persisted as `waiting-review`; this includes `compose-video`. Failed or invalid-output calls set `next_stage` to null and return a fix action. Executor identity conflicts are rejected as an internal contract result and are never reflected into the envelope.
