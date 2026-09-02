# CORE-RUNTIME-007: full-suite input/start boundary diagnosis

- Owner: WORKER_CORE
- Status: PM_DECISION
- Priority: P0
- Depends on: `CORE-RUNTIME-006=APPROVED`
- Branch: `feat/mountain-core-runtime`
- Base commit: `de57fab`
- Model: `gpt-5.6-terra`
- Reasoning effort: `medium`

## External dependency record

- Dependency: the supervised Worker dispatcher at
  `dispatch_cli_agent.sh`, required to start `WORKER_CORE` through
  `run_worker_agent.sh`.
- State: unavailable from the repository and configured command path; no
  supervised Worker lease can therefore be created.
- Recovery condition: restore the dispatcher and its supervised wrapper, then
  re-dispatch this unchanged P0 task. Until then, no Worker runtime, Tester
  handoff, or MEDIA resume decision is valid.
- PM resolve-blocker event: `2ce3d5b0acb9c19960489ed4a6ca5a65b718604893376778608dc934cee127ba`
  reconfirmed this external dependency; no duplicate diagnosis task or Worker
  dispatch is authorized while it remains unavailable.
- PM disposition: `BLOCKED`; no next task is required until the dependency is restored.
- Latest PM decision for event `2ce3d5b0acb9c19960489ed4a6ca5a65b718604893376778608dc934cee127ba`: `BLOCKED` (idempotent); no dispatch, and M1 requires no next task until the dependency is restored.
- PM review event `96d0dedbc4e7fd105e143c6095ed14bde3ddc38b7627d371c7ab32a9bdf8abc1`: `BLOCKED`. No bound Tester report exists, and the unchanged unavailable-dispatcher record means no valid Worker handoff or Tester result can support approval. No next task is required until the dependency is restored.

## Goal

Diagnose and recover the reproducible full-suite timeout reported by
`MEDIA-PREFLIGHT-004` at `test_inputs_and_start_boundary`, without changing media
preflight behavior or broadening M1 scope. Establish the exact blocking
process/resource boundary and make the full suite complete normally when the
defect is in the shared runtime; otherwise produce bounded, reproducible evidence
that identifies the external dependency and preserves fail-closed behavior.

## Allowed surfaces

- Shared runtime lifecycle/startup/cleanup code directly implicated by the
  reproduction;
- A focused regression test or diagnostic harness that proves normal pytest exit
  and cleanup;
- `docs/agents/reports/CORE-RUNTIME-007.md`.

## Forbidden surfaces

- `web-v2`, stage orchestration, Work Order semantics, media preflight feature
  behavior, or `MEDIA-E2E-003`;
- Disabling, skipping, weakening, or extending test timeouts to mask the hang;
- Starting user-owned external services, secrets, or paid/content-generation calls.

## Acceptance

1. Reproduce the full-suite boundary with a bounded diagnostic command and name
   the blocking child/process/resource from observable evidence.
2. If a shared-runtime defect is found, add the smallest lifecycle fix and a
   regression test; the full pytest suite exits 0 without skips or an outer
   watchdog being treated as success.
3. If no repository defect exists, report the concrete external dependency,
   exact bounded reproduction, and cleanup evidence; do not modify the blocked
   media task to imply success.
4. No lingering child process, listener, or temporary artifact remains after
   the reproduction and test run.
5. Report is sanitized and states whether `MEDIA-PREFLIGHT-004` can be resumed;
   this task does not approve or dispatch `MEDIA-E2E-003`.

## Gates

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
git diff --check de57fab...HEAD
```

## Stop condition

Commit and push the CORE branch, write the bounded diagnosis/recovery report,
and hand off to Tester. Do not decide approval or modify MEDIA task status.
