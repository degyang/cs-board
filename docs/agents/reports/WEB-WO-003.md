# WEB-WO-003 Worker Report

- Contract: `docs/agents/tasks/WEB-WO-003.md`
- Coordination commit: `26d1c18f7db313b225331d84a7c2089fb65a3e4c`
- Base: `9db741f`
- Implementation commit: `efb656cdfa695af48ee2af7baa5a2f11bd6d79f4`
- Branch: `feat/mountain-webui-surface-parity`

## Delivered

The Task Workbench now consumes the persisted execution-plan DTO, submits `auto/selective` and canonical manual-stage selections with input saves, and exposes all six stages' read-only Work Order summaries through the real API adapter. The summary shows identity-level status, revision/fingerprint, next action, safe artifact summaries, expected outputs, and relative file references. It does not render command argv, prompts/scripts, secrets, absolute paths, or raw backend fields. No backend, import/accept semantics, or mock business data were changed.

Files:

- `web-v2/src/lib/api/client.ts`
- `web-v2/src/lib/api/types.ts`
- `web-v2/src/pages/TaskWorkbenchPage.tsx`
- `web-v2/tests/work-order.test.tsx`

## Gates

| Command | Result |
| --- | --- |
| `npm --prefix web-v2 run build` | pass; TypeScript and Vite build |
| `npm --prefix web-v2 test -- --run` | pass; 17 files, 351 tests |
| `npm --prefix web-v2 run test:contract-checker` | pass; 2 files, 50 tests |
| `env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py --port 8765` | exit 0; real backend, production checker, API smoke, process/temp cleanup passed |
| `npm --prefix web-v2 test -- --run tests/work-order.test.tsx` | pass; 2 tests |
| `if rg -n 'Project|project_id|/projects' web-v2/src web-v2/scripts; then exit 1; else echo 'forbidden-pattern scan: no matches'; fi` | exit 0; no matches |
| `git diff --check` | pass |

The real checker used a temporary backend data directory and port 8765; the backend was stopped after the gate. An isolated browser attempt using `web-v2/scripts/verify-task-intake-e2e.mjs` exited 1 because its existing response waiter timed out after the POST `/tasks` request (`Failed to fetch` alert); no browser pass is claimed from that attempt. No dashboard/teamctl command was run.

## Evidence and state

- Work Order API path: `GET /tasks/{task_id}/runs/{run_id}/work-orders/{stage}`.
- Focused tests prove stage-specific fetch, safe rendering, and canonical manual-stage serialization.
- Worktree had no tracked changes before this report update. The smoke gate cleaned its temporary backend directory; the failed browser attempt left only ignored `.e2e-runtime/reference.wav`. The supervised runtime's untracked `.agents/coordination/runtime/WEB.json` is preserved and excluded from delivery.
- This report update is the delivery commit for the verified branch state; push and PM notification follow it.
