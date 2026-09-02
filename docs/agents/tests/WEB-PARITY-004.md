# WEB-PARITY-004 测试记录

Result: `PASS`

## Scope

- Contract: `docs/agents/tasks/WEB-PARITY-004.md`
- Delivery verified: `9db741fb5b230603b1cf340bc3e75b31bee31c4d`
- Dispatch base: `51656c91bb378d3a62ce5668d9d1c8b861de4847`
- Verification checkout: detached, exact delivery commit. No implementation files were changed.

## Contract gates

| Gate | Exact evidence | Result |
| --- | --- | --- |
| Build | `npm --prefix web-v2 run build` exited 0; `tsc --noEmit && vite build` completed, 68 modules transformed. | PASS |
| Unit tests | `npm --prefix web-v2 test -- --run` exited 0; 16 test files and 349 tests passed. | PASS |
| Real API contract | A fresh Mountain backend at `http://127.0.0.1:8000/api/v1` was started with an isolated temporary data directory. `MOUNTAIN_API_BASE=http://127.0.0.1:8000/api/v1 node web-v2/scripts/check-api-contract.mjs` exited 0 and printed `All contracts aligned against real backend ✓`. | PASS |
| Browser parity | With the production Vite proxy configuration `VITE_API_BASE_URL=/api/v1`, `WEBUI_BASE=http://127.0.0.1:5275 MOUNTAIN_API_BASE=http://127.0.0.1:8000/api/v1 GOLDEN_VIEWPORT=1366x900 node web-v2/scripts/verify-prototype-parity-e2e.mjs` exited 0 and printed `WEB-PARITY-004 parity verified: 5 groups at 1366x900 DPR1`. The verifier recorded zero console errors, page errors, failed requests, and API HTTP errors. | PASS |
| Whitespace diff | `git diff --check 51656c91bb378d3a62ce5668d9d1c8b861de4847...9db741fb5b230603b1cf340bc3e75b31bee31c4d` exited 0. | PASS |
| Forbidden-pattern audit | The contract's `git diff --unified=0 ... -- web-v2/src web-v2/scripts | rg ...` audit returned no added matches, including no literal `/projects`, mock/localStorage fallback, secret, or Authorization pattern. | PASS |

## Evidence inspection

- The browser verifier validated five immutable golden files and five fresh actual captures, each `1366×900`, DPR 1, with manifest hashes and route mappings.
- I visually opened all ten PNGs: brand shell, task queue, six-tab task creation, settings, and assets for both golden and actual. The actual pages retain the full branded sidebar and intended page hierarchy; the queue/assets differences are real empty-state/API data rather than copied prototype fixtures.
- The temporary API and Vite processes were stopped after the run; no dashboard runtime was changed.

This is a tester result only; it does not approve, merge, or change task state.
