# M07 Web Execution Plan 23 Task Contract

Task ID: `M07-WEB-EXECUTION-PLAN-23`
Owner: Web worker
State: `READY`
Base: `60762c54c57de46790d7c8ab826b7314b8099fa5`

## Goal

Connect `web-v2` to the committed backend execution-plan API contract from
`971494e150adf5321572505e85642687a3168487`.

## Allowed scope

- `web-v2/src/**` and focused `web-v2/tests/**` changes for task inputs and
  start feedback.
- Add typed DTOs for `execution_plan`, saved inputs, and the standard domain
  error response.
- Send/read `execution_mode` and `manual_stages` through the existing task-input
  form; display saved plan readback.
- Start using `POST /tasks/{task_id}/runs/{run_id}/start`; render the existing
  selective-plan `409 EXECUTION_PLAN_NOT_READY`, `retryable: false`, and safe
  `details.suggestion` as a user-facing notice.

## Explicit non-goals

- No Stage Work Order.
- No selective execution orchestration, stage scheduling, or new backend API.
- No `web/` legacy-surface changes and no secret/path/traceback rendering.

## Acceptance evidence

- Tests prove canonical plan form serialization/readback and the 409 suggestion
  view without exposing arbitrary server details.
- Existing Web test/build/type-check commands from `web-v2/package.json` pass.
- `git diff --check` passes; report exact commands/counts and commit hashes in
  `docs/Mountain/m07-web-execution-plan-23-report.md`.
- Commit implementation as `feat(mountain-web): surface execution plan controls`
  and report as `docs(mountain): report execution plan web evidence`.

## Stop condition

Stop after this display-and-feedback slice.  Do not implement manual-stage
execution or enter Stage Work Order.
