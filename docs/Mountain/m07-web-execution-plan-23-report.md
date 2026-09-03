# M07 Web Execution Plan 23 Report

Task: `M07-WEB-EXECUTION-PLAN-23`
Branch: `feat/mountain-assets-settings-web`
Base documented by contract: `60762c54c57de46790d7c8ab826b7314b8099fa5`

## Delivery

- Implementation commit: `8df79841ebfa60f360cc0d69367bd87c4470bb7f`
- Report commit: recorded below after this report is committed.
- No push was performed.

The pending-run input editor now writes `execution_mode` and canonical,
JSON-serialized `manual_stages`, restores the saved execution plan, and shows
the saved plan in the form. The HTTP client recognizes the standard domain
error envelope. A start response is shown as a plan notice only when it is
the documented `409 EXECUTION_PLAN_NOT_READY` with `retryable: false`; only a
string `details.suggestion` is included, never arbitrary detail fields.

Changed implementation files:

- `web-v2/src/lib/api/types.ts`
- `web-v2/src/lib/api/client.ts`
- `web-v2/src/pages/TaskWorkbenchPage.tsx`
- `web-v2/tests/execution-plan.test.tsx`
- `web-v2/tests/http-contract.test.ts`

## Evidence

| Command | Result |
| --- | --- |
| `npm test -- tests/execution-plan.test.tsx tests/http-contract.test.ts` | exit 0; 2 files, 30 tests passed |
| `npm run build` | exit 0; TypeScript no-emit check and Vite production build passed |
| `npm test` | exit 0; 15 files, 346 tests passed |
| `git diff --check` | exit 0; no whitespace errors |

The focused tests prove canonical stage ordering in form serialization,
saved-plan display, standard-error parsing, and safe rendering of the 409
suggestion without an unrelated server detail.

Known gaps: none within this display-and-feedback slice. No Stage Work Order,
selective orchestration, backend API, or legacy `web/` surface was changed.
