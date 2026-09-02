# WEB-PARITY-004 delivery report

## Result

REVIEW_READY. The production WebUI shell now follows the frozen Mountain brand hierarchy: full pinned sidebar, 山野小读 / MOUNTAIN STUDIO identity, ordered task/assets/settings/help navigation, and centered content framing. Task routes and real `/api/v1` integration remain unchanged.

## Evidence

- Manifest: `docs/Mountain/webui-parity-evidence/WEB-PARITY-004/manifest.json`
- Same-size DPR1 screenshots: `actual/brand-shell.png`, `actual/task-queue.png`, `actual/task-create-six-tabs.png`, `actual/settings.png`, `actual/assets.png`
- Golden reference: `docs/Mountain/webui-prototype-baseline/screenshots/settings/`
- The browser verifier asserted the full shell labels, six create tabs, real task API reachability, and zero console errors, page errors, failed requests, or API responses >=400.

## Gates

| Gate | Result |
| --- | --- |
| `npm --prefix web-v2 run build` | PASS, normal exit |
| `npm --prefix web-v2 test -- --run` | PASS, 16 files / 349 tests |
| `MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs` | PASS against live backend |
| `WEBUI_BASE=http://127.0.0.1:5275 MOUNTAIN_API_BASE=http://127.0.0.1:8000 GOLDEN_VIEWPORT=1366x900 node web-v2/scripts/verify-prototype-parity-e2e.mjs` | PASS, 5 groups, DPR1 |
| `git diff --check 51656c91bb378d3a62ce5668d9d1c8b861de4847` | PASS |
| forbidden-pattern audit for `web-v2/src` and `web-v2/scripts` | PASS, no matches |

## Scope

Changed only `web-v2/src/components/layout/Sidebar.tsx`, `web-v2/src/styles/app.css`, the parity verifier, and this report/evidence set. No backend, prototype, pipeline, WO, approval, or merge changes were made.

## Attempt 2 correction handoff

The prior independent review requested immutable five-page golden inputs, per-file hashes, complete route mapping, and a verifier that opens/validates those inputs. This attempt preserves the prior delivery and adds the approved prototype golden set under `docs/Mountain/webui-parity-evidence/WEB-PARITY-004/golden/`, its source/hash manifest, and fail-closed validation in `web-v2/scripts/verify-prototype-parity-e2e.mjs`.

- Golden source: approved prototype commit `0f56e824c0d49ab5c090e7ea07086dc9d47f47a9`, source path `prototypes/webui`, read-only preview origin `http://127.0.0.1:5182`; all five source hashes match the approved manifest byte-for-byte.
- Production/golden route pairs: `/help`↔`/help` (brand shell), `/`↔`/projects` (task queue visual mapping), `/tasks/new`↔`/create` (six tabs), `/settings/models`↔`/settings`, and `/assets`↔`/assets`.
- Actual captures: `actual/brand-shell.png`, `actual/task-queue.png`, `actual/task-create-six-tabs.png`, `actual/settings.png`, `actual/assets.png`; all are 1366×900, DPR1, 100% zoom. The verifier records each actual and golden SHA-256 in `manifest.json`.
- Manual visual inspection confirmed each actual/golden pair is openable and corresponds to the intended shell, queue, six-tab create, settings, and assets surface; real API data/empty states remain production-specific and no prototype mock state was copied.

## Attempt 2 gates

| Command | Exit | Result |
| --- | ---: | --- |
| `npm --prefix web-v2 run build` | 0 | PASS |
| `npm --prefix web-v2 test -- --run` | 0 | PASS, 16 files / 349 tests |
| `MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs` | 0 | PASS against isolated live backend |
| `WEBUI_BASE=http://127.0.0.1:5275 MOUNTAIN_API_BASE=http://127.0.0.1:8000 GOLDEN_VIEWPORT=1366x900 node web-v2/scripts/verify-prototype-parity-e2e.mjs` | 0 | PASS, five paired groups; browser counters all zero |
| `git diff --check 51656c91bb378d3a62ce5668d9d1c8b861de4847...HEAD` | 0 | PASS |
| forbidden-pattern audit from the contract | 0 | PASS, no matches |

The live backend used an isolated `/tmp/cs-board-web-parity-data` directory and the WebUI used `VITE_API_BASE_URL=/api/v1` with the Vite proxy. Both temporary servers were stopped after evidence capture; no backend or prototype files were changed. Implementation/evidence delivery commit: `cdda8725e7c23ad8dfa9b3d6548d8d7e4323bd1c`. Branch: `feat/mountain-webui-surface-parity`.

Worktree state at handoff: all tracked task files are committed and pushed; the only untracked path is the dashboard’s ephemeral `.agents/coordination/runtime/` lease files created for this worker session.
