# WEB-INTAKE-003 交付报告

状态：`REVIEW_READY`

基线：`7dc2a93`，恢复 HEAD：`0b99b50`，分支：`feat/mountain-webui-surface-parity`

## Delivery

- 上一轮已审核交付 `672f820` 与 attempt 2 纠正 `0dbbf4e` 保持不变；本轮只完成评审列出的 attempt 3 有界纠正。
- 修正涉及 `web-v2/scripts/check-api-contract.mjs`、
  `web-v2/scripts/contract-checker-core.mjs` 和
  `web-v2/tests/contract-checker-exec.test.ts`。
- 推送分支：`feat/mountain-webui-surface-parity`。
- 现有真实浏览器证据和 manifest 来自 `672f820`，本轮保留且未重新生成。
- 未修改 `WEB-WO-003`，未进入 Pipeline/Work Order 页面，未合并任何分支。

## Real run

- API 启动命令形状：`CSBOARD_DATA_DIR=<temporary-data-dir> CSBOARD_ALLOW_PLAINTEXT_SECRETS=1 <python> -m uvicorn webapp.mountain_server:app --host 127.0.0.1 --port 8000`；测试后已停止。
- Web 启动命令形状：`VITE_API_BASE_URL=/api/v1 npm --prefix web-v2 run dev -- --host 127.0.0.1 --port 5275`；通过 Vite `/api` 同源代理访问 API，测试后已停止。
- API：`127.0.0.1:8000`；Web：`127.0.0.1:5275`。
- 浏览器创建单个 Task；task ID 仅以 SHA-256 摘要记录：
  `a5502c295e258623951c30254014d58d70f1a8d704936e05fe8dc58fa9b9de80`。
- 脱敏文案 SHA-256：
  `4aaaa812cdbdf24ea8f378fbb0226b38522f94f246a3b6a367a42542dfc9b1f5`，长度 `45`。
- 浏览器请求未包含 `/start`、`/pipeline/` 或 stage `run/retry`；console error/warning、pageerror、failed request 和 HTTP >=400 均为 `0`。

## Attempt 3 gates

每项最终执行均正常退出（exit `0`）：

```text
npm --prefix web-v2 test -- --run tests/contract-checker-exec.test.ts
  ✓ 17 tests passed; silent-backend subprocess exits non-zero and near-boundary valid response passes

npm --prefix web-v2 test -- --run
  ✓ 16 files / 349 tests passed

npm --prefix web-v2 run build
  ✓ Vite production build

MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs
  ✓ All contracts aligned against real backend

git diff --check 0dbbf4e...HEAD
  ✓ exit 0

report-path redaction scan
  ✓ exit 0; no absolute paths

rg -n 'VITE_API_BASE_URL=/api/v1|<temporary-data-dir>|<installed-chromium>' docs/agents/reports/WEB-INTAKE-003.md
  ✓ exit 0; startup shape and redaction placeholders present

Previously accepted browser command shape:
`WEBUI_BASE=http://127.0.0.1:<web-port> MOUNTAIN_API_BASE=http://127.0.0.1:<api-port> PLAYWRIGHT_CHROMIUM_EXECUTABLE=<installed-chromium> node web-v2/scripts/verify-task-intake-e2e.mjs`

The live checker uses its internal seven-second per-request abort deadline by default;
`MOUNTAIN_API_REQUEST_TIMEOUT_MS` provides a bounded test override. The focused test
starts a silent local HTTP server, runs the checker CLI with a 25 ms deadline, observes
the CLI's own non-zero exit, and cleans up the child process and server. A second real
local server delays one valid response by 5.5 seconds and the checker CLI passes without
an override, proving the default does not kill the backend's legal probe boundary.
```

The original attempt-1 browser evidence remains the accepted positive path. Review
explicitly bounded attempt 3 to checker/test/report corrections, so no browser run or
evidence regeneration was performed in this correction.

## Evidence manifest

Manifest: `docs/Mountain/webui-parity-evidence/tasks/intake-manifest.json`

- `intake-created.png`: `feb51a3d556f0ef48f0311e9931a1fbfdc136bd109eb2f48c796800f6593ad9b`
- `intake-queue.png`: `3e084e4213543413f7f4e13b49c0321621d88933c4d18d6154ab4cd326409e89`
- `intake-workbench.png`: `fd27d8bab16a5a463fe3a1cf9faedb179fa747ecb1acac3b5cfd8a2b18c48bb2`
- manifest SHA-256: `bc1b5f7e5b5bc3857706721d19fe8ddc6abeb02dd35514421e7720ae8e6b36eb`

## Final state

- Report and evidence from `672f820` remain unchanged; attempt 2 corrections remain intact; this attempt 3 correction is ready to commit and push.
- No known product gaps remain for this contract.
