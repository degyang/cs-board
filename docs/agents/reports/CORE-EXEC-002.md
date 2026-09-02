# CORE-EXEC-002 report

## Actual change

Base: `a5d5938` (`feat/mountain-assets-settings-backend`).

The persisted `tasks/<task_id>/request.json.execution_plan` is now the only
execution-decision input for `MountainCommands.start_run`, `pipeline_run`,
`pipeline_resume`, `stage_run`, and `stage_retry`.  The `/api/v1` stage route
uses `stage_run`; CLI stage commands use the same entrypoint.

`selective.manual_stages` are manual gates.  The orchestrator executes the
automatic prefix, stops before the next untriggered manual stage, and does not
change that Stage status.  An explicit stage run/retry can trigger only that
manual stage; a targeted request for a later stage still stops at an earlier
manual gate.  Task-level locking serializes concurrent command calls for the
same task so an automatic prefix cannot execute twice in one process.

`get_inputs` now reads the persisted `task.json` document for
`script_preparation` and `visual_anchor_enabled`, rather than serializing the
stable `Task` domain DTO (which intentionally does not retain extra persisted
fields).

## Contract Decision

No StageStatus value was added.  A waiting decision is a normal successful
pipeline response:

```json
{
  "ok": true,
  "state": "waiting-manual-trigger",
  "next_stage": "clone-voice",
  "manual_stages": ["clone-voice", "compose-video"],
  "stages_executed": ["generate-visual-anchors"]
}
```

This is backward-compatible for auto plans: their existing response shape and
six-stage order remain unchanged.  Existing/old input requests without an
`execution_plan` deterministically read as `{ "mode": "auto",
"manual_stages": [] }`.

## Verification

- `pytest -q tests/test_task_execution_plan_23.py tests/test_pipeline_orchestrator.py tests/test_cli_csboard.py tests/test_mountain_contracts.py tests/test_mountain_server.py`
  - `103 passed`
- Full backend collection: `493 tests collected`.
- Full suite was run in four bounded groups due the 30-second command ceiling:
  - 94 passed (+ 3 subtests)
  - 63 passed
  - 96 passed, 4 skipped
  - 235 passed, 1 skipped
  - Total: 488 passed, 5 skipped.

Added behavior coverage includes first/manual/multiple gates, automatic prefix,
targeted non-bypass, CLI subprocess decision parity, input round-trip fidelity,
and concurrent pipeline calls not duplicating the automatic prefix.

## Known limits / non-goals retained

- No Stage Work Order, external asset acceptance, or media E2E was added.
- No `web-v2` or old `/api/mountain` change was made.
- Task lifecycle synchronization and legacy CLI provider configuration remain
  outside this slice.
