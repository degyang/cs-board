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
