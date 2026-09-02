# WEB-INTAKE-003 交付报告

状态：`REVIEW_READY`

基线：`7dc2a93`，恢复 HEAD：`0b99b50`，分支：`feat/mountain-webui-surface-parity`

## Delivery

- 仅消费已审核、自包含后端实现 `6699d20`，其直接子提交在本工作树中为
  `113dc2e fix(mountain): expose fail-closed secret availability`。
- 推送分支：`feat/mountain-webui-surface-parity`。
- 后端改动仅来自上述消费提交：补齐
  `FilesystemServiceRegistry.has_required_secrets` 及行为测试。
- 新增真实浏览器证据：
  `docs/Mountain/webui-parity-evidence/tasks/intake-created.png`、
  `intake-queue.png`、`intake-workbench.png` 和 `intake-manifest.json`。
- 未修改 `WEB-WO-003`，未进入 Pipeline/Work Order 页面，未合并任何分支。

## Real run

- API：`127.0.0.1:8000`，临时数据目录 `/tmp/web-intake-003.7Dv4Ts`，测试后已停止。
- Web：`127.0.0.1:5275`，Vite `/api` 代理到上述 API，测试后已停止。
- 浏览器创建单个 Task；task ID 仅以 SHA-256 摘要记录：
  `a5502c295e258623951c30254014d58d70f1a8d704936e05fe8dc58fa9b9de80`。
- 脱敏文案 SHA-256：
  `4aaaa812cdbdf24ea8f378fbb0226b38522f94f246a3b6a367a42542dfc9b1f5`，长度 `45`。
- 浏览器请求未包含 `/start`、`/pipeline/` 或 stage `run/retry`；console error/warning、pageerror、failed request 和 HTTP >=400 均为 `0`。

## Required gates

每项最终执行均正常退出（exit `0`）：

```text
npm --prefix web-v2 run build
  ✓ Vite production build

npm --prefix web-v2 test -- --run
  ✓ 16 files / 347 tests passed

MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs
  ✓ All contracts aligned against real backend

WEBUI_BASE=http://127.0.0.1:5275 \
MOUNTAIN_API_BASE=http://127.0.0.1:8000 \
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/home/ubuntu/.cache/ms-playwright/chromium-1187/chrome-linux/chrome \
node web-v2/scripts/verify-task-intake-e2e.mjs
  ✓ six-tab create/save/readback, queue search, workbench readback, 3 screenshots, browser_issues=0

git diff --check 7dc2a93...HEAD
  ✓ exit 0

! rg -n 'Project|project_id|/projects|mockResolvedValue' web-v2/scripts/verify-task-intake-e2e.mjs
  ✓ exit 0; no matches
```

The first browser launch attempt also ran the required script but exited non-zero because
the default Playwright Chromium headless shell was absent. The same gate was rerun to
normal exit with the already-installed Chromium executable above; no source or acceptance
criteria were changed.

## Evidence manifest

Manifest: `docs/Mountain/webui-parity-evidence/tasks/intake-manifest.json`

- `intake-created.png`: `feb51a3d556f0ef48f0311e9931a1fbfdc136bd109eb2f48c796800f6593ad9b`
- `intake-queue.png`: `3e084e4213543413f7f4e13b49c0321621d88933c4d18d6154ab4cd326409e89`
- `intake-workbench.png`: `fd27d8bab16a5a463fe3a1cf9faedb179fa747ecb1acac3b5cfd8a2b18c48bb2`
- manifest SHA-256: `bc1b5f7e5b5bc3857706721d19fe8ddc6abeb02dd35514421e7720ae8e6b36eb`

## Final state

- Report and evidence are ready to commit and push with the delivery.
- No known product gaps remain for this contract.
