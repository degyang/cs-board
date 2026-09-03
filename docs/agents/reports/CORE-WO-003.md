# CORE-WO-003 report

## Delivery

Code commit: `3836002 feat(mountain): add stage work order skeleton`.

This slice adds a Stage Work Order v1 backend skeleton only. It does not
implement candidate import, validate, accept/reject/retry side effects, media
execution, WebUI changes, or legacy API changes.

## DTO decision and paths

- `StageWorkOrder` is a separate domain DTO with schema version `1.0`, stable
  fingerprint-derived ID, revision, independent WO state machine, stage scope,
  input Artifact refs, safe parameter/instruction/output references, structured
  command slots, and explicit unavailable next action.
- WO state is intentionally separate from `Run` and `StageState`. The initial
  state projects persisted `ExecutionPlan`: selected manual stages are
  `waiting-manual-trigger`; all others are `ready`.
- Current files are persisted below
  `tasks/<task>/runs/<run>/work-orders/<stage>/`; current files are
  `work-order.json`, `parameters.json`, and `instructions.md`; immutable
  envelope history is in `revisions/<revision>/work-order.json`.
- Input fingerprint covers normalized identity, safe request summary, scope,
  and succeeded upstream Artifact refs. A changed fingerprint archives the old
  revision as `stale` and creates a new revision/ID.
- API: `GET /api/v1/tasks/{task}/runs/{run}/work-orders/{stage}`.
- CLI: `work-order show --task <task> --run <run> --stage <stage> --json`.
  Both call `MountainCommands.work_order_show`, the sole Application write and
  decision path.

The projected parameters expose a script SHA-256, not the script; no reference
audio, provider URL, secret, absolute path, or shell command is written. The
candidate Gate is represented only by empty structured command arrays and a
stable `CAPABILITY_NOT_AVAILABLE` next action.

## Verification

- Required focused gate:

  ```text
  /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
    tests/test_stage_work_orders.py tests/test_mountain_contracts.py tests/test_cli_csboard.py
  21 passed, exit 0
  ```

- Full backend suite was run in bounded groups due the 30-second terminal
  ceiling; every group exited 0:
  - `25 passed`; `72 passed, 3 subtests passed`; `29 passed`; `34 passed`;
    `96 passed, 4 skipped`; `241 passed, 1 skipped`.
- `git diff --check e1bc3d5...HEAD`: exit 0.
- `! rg -n '/mnt/|[A-Za-z]:\\\\|api[_-]?key|tts[_-]?url' tests/fixtures/stage-work-orders`:
  exit 0; fixture directory exists and has no prohibited text.

Behavior tests cover all six deterministic/schema-valid envelopes, same-input
ID/fingerprint stability, manual status projection, persisted current files,
upstream Artifact-driven new revision plus stale audit record, API/CLI equality
and secret/script/path absence, and domain path/state validation.

## Known unimplemented Gate

Candidate import, validation, acceptance, rejection and retry are deliberately
not implemented. Their command arrays remain empty and the response states the
next action explicitly; no formal Artifact is fabricated and no candidate can
be accepted by this slice.

## Attempt 2 — readiness semantic correction

Code commit: `b3500e0 fix(mountain): enforce work order readiness`.

- Missing required upstream Artifacts now produce `DEPENDENCY_NOT_READY` with
  stable `missing_artifact_keys` from both API and CLI. No current WO directory
  is created for a previously unseen missing dependency; an existing WO is
  archived stale if its dependency later disappears.
- Non-external stages now expose exactly one structured `commands.run` command
  with argv array, deterministic UUID idempotency key, and revision/input
  preconditions. Their next action is `RUN_AVAILABLE` or
  `MANUAL_TRIGGER_REQUIRED` from persisted `ExecutionPlan`.
- `generate-illustrations` remains explicitly unavailable with no run command;
  no candidate side effect was added. Its directory is now exactly
  `manual/illustrations/candidates/<work_order_id>`.
- The JSON schema now rejects unknown fields and validates nested identity,
  scope, artifact, command, argv, next-action and relative-path structure.

### Attempt 2 verification

- Focused gate: `23 passed`, exit 0.
- Full backend groups all exited 0: `25 passed`; `72 passed, 3 subtests`;
  `29 passed`; `34 passed`; `96 passed, 4 skipped`; `243 passed, 1 skipped`.
- `git diff --check e1bc3d5...HEAD` and the fixture sensitive-path scan both
  exited 0.

## Attempt 3 — final output and stale-recovery correction

Code commit: `a868ace fix(mountain): restore stale work orders safely`.

- `expected_outputs` is now a per-stage collection: clone voice declares both
  `audio.voice-manifest` and `timing.timeline`; compose video declares both
  `output.final-video` and `output.final-manifest`; all other stage keys stay
  unchanged.
- A current stale WO is no longer returned merely because its restored inputs
  reproduce the same fingerprint. Restoration creates a new revision, a new
  `work_order_id`, and therefore a new structured run idempotency identity.

Verification: focused gate `24 passed`; final broad backend group `244 passed,
1 skipped`, all exit 0. Full grouped suite evidence from attempt 2 remains
applicable for unaffected groups; no scope outside these two corrections was
changed.
