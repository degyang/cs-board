# WEB-WO-003 Test Report

- Role: `TESTER_WEB`
- Contract: `docs/agents/tasks/WEB-WO-003.md`
- Delivery under test: `7adc8f5167602cc321e9467a15431efc6dbafd0f`
- Result: **FAIL**

## Verdict

The delivery does not meet the acceptance boundary requiring browser evidence. The isolated real-browser Task creation gate exits `1`: it sends `POST /api/v1/tasks`, then times out waiting for the create/input responses and displays `Failed to fetch`. No passing browser evidence is present at this delivery; its Worker report also explicitly records this failed attempt.

## Gates run against the exact detached delivery

| Gate | Result | Exact evidence |
| --- | --- | --- |
| `npm --prefix web-v2 run build` | PASS | Exit `0`; Vite built 68 modules in `877ms`. |
| `npm --prefix web-v2 test -- --run` | PASS | Exit `0`; `17` test files and `351` tests passed. |
| `npm --prefix web-v2 run test:contract-checker` | PASS | Exit `0`; `2` test files and `50` tests passed. |
| `env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python scripts/smoke_real_backend_contract.py --port 8765` | PASS | Exit `0`; health, encrypted secret store, production contract checker, API smoke, process cleanup, and temporary-directory cleanup passed. |
| `npm --prefix web-v2 test -- --run tests/work-order.test.tsx` | PASS | Exit `0`; `1` test file and `2` tests passed. React Router future-flag warnings only. |
| `if rg -n 'Project|project_id|/projects' web-v2/src web-v2/scripts; then exit 1; else echo 'forbidden-pattern scan: no matches'; fi` | PASS | Exit `0`; no matches. |
| `git diff --check 9db741f 7adc8f5` | PASS | Exit `0`; no whitespace errors. |
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/home/ubuntu/.cache/ms-playwright/chromium-1187/chrome-linux/chrome WEBUI_BASE=http://127.0.0.1:5275 MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/verify-task-intake-e2e.mjs` | FAIL | Exit `1`: `create/inputs response timeout; requests=GET /api/v1/tasks,GET /api/v1/assets/styles,GET /api/v1/assets/voices,GET /api/v1/health,GET /api/v1/tasks,GET /api/v1/assets/styles,GET /api/v1/assets/voices,GET /api/v1/health,POST /api/v1/tasks; alerts=[\"Failed to fetch\"]`. |

## Browser setup and scope

The failing browser command used an isolated temporary backend data directory, backend `127.0.0.1:8000`, Vite `127.0.0.1:5275`, and the pinned Chromium executable. Both started processes were stopped after the gate. No dashboard runtime was changed. The report covers only this test result and makes no approval decision.
