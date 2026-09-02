# WEB-WO-003 测试记录

Result: `FAIL`

## Scope

- Contract: `docs/agents/tasks/WEB-WO-003.md`
- Delivery verified: `7adc8f5167602cc321e9467a15431efc6dbafd0f`
- Delivery base: `9db741fb5b230603b1cf340bc3e75b31bee31c4d`
- Verification occurred against the assigned delivery worktree. No implementation or dashboard runtime was changed.

## Contract gates

| Gate | Exact evidence | Result |
| --- | --- | --- |
| Production build | `/home/ubuntu/.local/share/mise/installs/node/24.15.0/bin/npm --prefix web-v2 run build` exited 0; `tsc --noEmit && vite build` completed and transformed 68 modules. | PASS |
| Full Web test suite | `/home/ubuntu/.local/share/mise/installs/node/24.15.0/bin/npm --prefix web-v2 test -- --run` exited 0; 17 test files and 351 tests passed. | PASS |
| Contract-checker tests | `/home/ubuntu/.local/share/mise/installs/node/24.15.0/bin/npm --prefix web-v2 run test:contract-checker` exited 0; 2 files and 50 tests passed. | PASS |
| Focused Work Order interaction | `/home/ubuntu/.local/share/mise/installs/node/24.15.0/bin/npm --prefix web-v2 test -- --run tests/work-order.test.tsx` exited 0; 2 tests passed. | PASS |
| Real backend API contract | `env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/Workstation/Projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py --port 8765` exited 0. It started an isolated encrypted-data backend, and the production checker printed `All contracts aligned against real backend`; the smoke endpoints passed and the process/temp directory were cleaned up. | PASS |
| Forbidden-pattern audit | `if rg -n 'Project|project_id|/projects' web-v2/src web-v2/scripts; then exit 1; else echo 'forbidden-pattern scan: no matches'; fi` exited 0 and printed `forbidden-pattern scan: no matches`. | PASS |
| Whitespace diff | `git diff --check 9db741f..7adc8f5` exited 0. | PASS |
| Browser evidence | The contract requires browser evidence. The delivery's own `docs/agents/reports/WEB-WO-003.md` records that `web-v2/scripts/verify-task-intake-e2e.mjs` exited 1 after the POST `/tasks` response waiter timed out, with a `Failed to fetch` alert, and explicitly claims no browser pass. Independent reruns could not start the isolated Vite server because the contract port `127.0.0.1:5175` was already occupied; Vite exited 1 with `Error: Port 5175 is already in use`. The existing listener was not stopped or changed. | FAIL |

## Verdict basis

The build, component, API, and static gates pass, but the acceptance boundary expressly requires browser evidence. There is a recorded browser-gate failure and no passing browser evidence for this delivery. Therefore the work order cannot pass validation.

This is a TESTER_WEB result only. It does not approve, merge, alter task status, dispatch work, or change dashboard runtime.
