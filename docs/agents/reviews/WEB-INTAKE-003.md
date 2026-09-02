# WEB-INTAKE-003 独立评审

Verdict: `CHANGES_REQUESTED`

## 评审范围

- 契约基线：`7dc2a9388faf7d79e991bda0056cca956f1e74ba`；
- 交付提交：`672f820eef848592d893de931227139d9518b589`；
- 评审差异：`git diff 7dc2a93...672f820`；
- 交付分支 `feat/mountain-webui-surface-parity` 干净，HEAD 与同名远端分支一致。

任务新增的 intake 脚本、报告和三张证据位于允许范围；其余 Python 变更来自契约明确允许消费的
`CORE-CAP-004` 和 `CORE-CAP-005` 交付。未修改 Work Order 页面，浏览器请求也未进入 Start、
Pipeline 或 Stage run/retry。

## 已通过行为

1. 独立使用临时 data dir 启动真实 Mountain API，并通过 Vite 的 `/api` 同源代理运行真实
   Chromium；创建、保存、队列定位、重新打开和工作台回读均成功。
2. 浏览器实际只发出一次 `POST /api/v1/tasks` 和一次对应的 `POST /inputs`；请求清单中没有
   `/start`、`/pipeline/` 或 Stage `run/retry`，`browser_issues=0`。
3. 文案 hash/长度、分割规则、风格、锚点、字幕、pen/stroke 和 204 B WAV 元数据均回读一致；
   缺失 Web 服务时 intake 脚本在自身 30 秒导航超时后 exit 1，而非假通过。
4. 三张提交截图已逐张目视检查：创建完成、队列唯一结果和工作台回读都可见；manifest 的三个
   SHA-256 与字节数均和文件一致，manifest 不含文案、Secret 或绝对路径。
5. 交付后没有残留 API、Vite、Chromium、intake Node 进程或临时 worktree；原 WEB 工作树保持干净。

## 独立门禁

以下门禁均实际执行并正常退出：

```text
npm --prefix web-v2 run build
Vite production build passed; exit 0; 5.5s

npm --prefix web-v2 test -- --run
16 files / 347 tests passed; exit 0; 16.6s

python -m pytest -q tests/test_service_registry.py tests/test_capabilities_api.py
20 passed, 1 warning; exit 0; 1.7s

MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs
All contracts aligned against real backend; exit 0

VITE_API_BASE_URL=/api/v1 npm --prefix web-v2 run dev -- --host 127.0.0.1 --port 5276 --strictPort
WEBUI_BASE=http://127.0.0.1:5276 MOUNTAIN_API_BASE=http://127.0.0.1:8000 \
PLAYWRIGHT_CHROMIUM_EXECUTABLE=<installed-chromium> \
node web-v2/scripts/verify-task-intake-e2e.mjs
six-tab create/save/readback + queue + workbench passed; 3 screenshots; browser_issues=0; exit 0

git diff --check 7dc2a93...672f820
exit 0

! rg -n 'Project|project_id|/projects|mockResolvedValue' \
  web-v2/scripts/verify-task-intake-e2e.mjs
exit 0
```

复验曾把 `VITE_API_BASE_URL` 误设为绝对 `http://127.0.0.1:8000/api/v1`，5276 因不在后端
CORS allowlist 而在创建时失败；改为交付报告所称的 `/api` 同源代理后稳定通过。这不是产品缺陷，
但暴露出交付报告缺少真实 Vite 启动参数，无法仅按报告命令复现成功运行。

另一个负向门禁未通过：在 API 服务未启动时执行契约列出的 `check-api-contract.mjs`，进程超过
60 秒仍未非零退出，Reviewer 手动发送 SIGINT 后退出 130。`contract-checker-core.mjs` 当前每个
请求直接调用无 signal/deadline 的 `fetch`，并串行遍历多个静态、动态与错误端点；现有网络失败测试
只覆盖本机端口 1 的立即拒绝，没有覆盖连接无响应或长连接超时。契约先把该 checker 列为 gate，紧接着
要求自动化脚本在“依赖缺失、服务未启动或 API 错误”时非零退出，因此这一失败属于本任务范围，不能用
外层 `timeout` 的 124 退出冒充脚本通过。

## 必须纠正

1. `docs/agents/reports/WEB-INTAKE-003.md` 把实际 `/tmp/...` data dir 和
   `/home/ubuntu/.../chrome` 写入了提交证据，违反契约“绝对路径不得进入证据”。将它们分别改为
   `<temporary-data-dir>` 与 `<installed-chromium>` 等脱敏占位符；保留实际端口与 hash。
2. 报告应补充启动真实服务所需的脱敏命令形状，明确 Vite 使用
   `VITE_API_BASE_URL=/api/v1` 同源代理以及测试后停止 API/Vite。当前只记录端口和 E2E 调用，
   没有记录决定复验成败的 Vite 启动参数。
3. 为 `check-api-contract.mjs` 的真实后端请求增加内部有界 deadline/abort，并让超时形成 violation 后
   由 CLI 自身 exit 1；不得依赖外层 `timeout`，也不得把超时降级为 fixture 成功。增加受控的无响应
   HTTP server/subprocess 行为测试，证明 CLI 在测试规定的上限内自行非零退出并清理子进程，同时保留
   现有真实后端成功路径。

## 有界返工范围

只修改 `web-v2/scripts/check-api-contract.mjs`、必要时的
`web-v2/scripts/contract-checker-core.mjs`、聚焦 checker 的既有测试文件，以及
`docs/agents/reports/WEB-INTAKE-003.md`。不改产品页面、API/DTO、截图、manifest 或任务契约。
完成后执行：

```text
! rg -n '/tmp/|/home/|/mnt/' docs/agents/reports/WEB-INTAKE-003.md
rg -n 'VITE_API_BASE_URL=/api/v1|<temporary-data-dir>|<installed-chromium>' \
  docs/agents/reports/WEB-INTAKE-003.md
npm --prefix web-v2 test -- --run tests/contract-checker-exec.test.ts
npm --prefix web-v2 test -- --run
MOUNTAIN_API_BASE=http://127.0.0.1:<live-api-port> node web-v2/scripts/check-api-contract.mjs
git diff --check 672f820...HEAD
```

新增测试必须观察 checker 子进程自身的非零退出码；测试框架的超时或外层 `timeout` 只可作为失败清理，
不得写成通过断言。无需重跑或重生成 Playwright 截图，因为 intake 正向浏览器行为已经独立通过且该范围
不触碰页面或 E2E 脚本。

Worker 提交并推送有界报告修正后，等待 CEO 再次安排独立复核。本 verdict 不批准任务、不合并，
也不触碰 `WEB-PARITY-004` 或 `WEB-WO-003`。
