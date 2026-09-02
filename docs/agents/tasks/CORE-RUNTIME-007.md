# CORE-RUNTIME-007: full-suite input/start boundary diagnosis

- Owner: WORKER_CORE
- Status: BLOCKED
- Priority: P0
- Depends on: `CORE-RUNTIME-006=APPROVED`
- Branch: `feat/mountain-core-runtime`
- Base commit: `de57fab`
- Model: `gpt-5.6-terra`
- Reasoning effort: `medium`

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
