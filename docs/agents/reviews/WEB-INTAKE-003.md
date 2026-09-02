# WEB-INTAKE-003 独立评审

Verdict: `APPROVED`

## 评审范围

- 契约基线：`7dc2a9388faf7d79e991bda0056cca956f1e74ba`；
- 交付提交：`672f820eef848592d893de931227139d9518b589`；
- attempt 2 交付：`0dbbf4e9f2759d11200b5c05435c809a2a51ec2c`；
- attempt 3 交付：`51656c91bb378d3a62ce5668d9d1c8b861de4847`；
- 评审差异：`git diff 7dc2a93...672f820`；
- attempt 2 差异：`git diff 672f820...0dbbf4e`；
- attempt 3 差异：`git diff 0dbbf4e...51656c9`；
- 交付分支 `feat/mountain-webui-surface-parity` 干净，HEAD 与同名远端分支一致。

任务新增的 intake 脚本、报告和三张证据位于允许范围；其余 Python 变更来自契约明确允许消费的
`CORE-CAP-004` 和 `CORE-CAP-005` 交付。未修改 Work Order 页面，浏览器请求也未进入 Start、
Pipeline 或 Stage run/retry。

## Attempt 3 最终复核

attempt 3 只修改 `contract-checker-core.mjs`、既有 checker 执行测试和交付报告；没有修改
`check-api-contract.mjs` 以外的产品行为、后端 probe、页面、API/DTO、E2E、截图或 manifest。

独立复验结果：

- 默认 request deadline 从 5 秒调整为 7 秒，`AbortController` 与受控 override 保持不变；
- focused test `17/17`，其中 silent backend 子进程约 0.4 秒内由 CLI 自身非零退出，
  `signal=null`、测试 kill timer 未触发、服务和子进程均关闭；
- 新增真实 subprocess 在不设置 timeout override 时让 voice-alignment 合法响应延迟 5.5 秒，CLI
  正常 exit 0、`signal=null`，证明不会再与后端 5 秒 probe 边界竞态；
- 全量前端 `16 files / 349 tests` 通过，production build 通过；
- 使用 fresh 临时 data dir 启动真实 Mountain API，明确 unset
  `MOUNTAIN_API_REQUEST_TIMEOUT_MS` 后运行 checker，voice-alignment 等全部端点返回，
  `All contracts aligned against real backend`，约 5 秒正常 exit 0；
- `git diff --check 0dbbf4e...51656c9`、有界文件集合、路径脱敏、同源生命周期和 intake forbidden
  scans 全部通过；报告所列 17/349 数量、7 秒默认值、5.5 秒回归与 live gate 均和独立证据一致；
- 真实 API、checker、测试 child process、端口和临时 worktree 均已清理；WEB 交付分支干净且
  `51656c9` 与同名远端一致。

本次最终复核未重新生成 attempt 1 已审核的浏览器截图，也未重跑无关产品链路，符合 attempt 3 的有界
范围。未发现阻塞性或非阻塞性问题。此处只记录 Reviewer verdict；任务状态、集成和后续派发由 CEO
决定，不包含对 `WEB-PARITY-004` 或 `WEB-WO-003` 的批准。

## Attempt 2 独立复核

attempt 2 严格只修改报告、`check-api-contract.mjs`、`contract-checker-core.mjs` 和既有 checker
执行测试，符合上轮有界范围。以下纠正已经通过：

- 报告不再包含 `/tmp`、`/home` 或 `/mnt` 绝对路径，并明确记录
  `VITE_API_BASE_URL=/api/v1`、临时 data dir、API/Vite 端口和测试后停止的命令形状；
- 实现使用内部 `AbortController`，CLI 允许受控覆盖 deadline；
- silent backend 测试启动真实本地无响应 HTTP server 和 checker 子进程。独立运行观察到测试的
  kill timer 未触发、checker 自身退出码非零、`signal=null`，不存在外层 timeout 假通过；
- focused `16/16`、全量前端 `348/348`、production build、diff、范围和 forbidden scans 均正常退出。

但 fresh 临时 data dir 的真实 Mountain API 正向门禁失败：

```text
MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs
Voice alignment: Request timed out after 5000ms
1 contract violation(s) found
exit 1
```

API 日志显示同次检查的 services、assets、toolchain、storage、diagnostics 和动态 service 端点均返回
200；`/settings/voice-alignment` 未能在 checker 的 5 秒 deadline 内完成。该 endpoint 在无缓存时会
调用 IndexTTS 的真实 probe，而 backend probe 自身就是 5 秒超时，因此 checker 默认 5 秒与被测端点
形成确定性的边界竞态。报告声称未设置 timeout override 的 live gate 已通过，与 fresh 独立复验不符。

### Attempt 2 必须纠正（attempt 3 已完成）

1. 调整 checker 的内部 timeout 策略，使 fresh data dir 的真实后端正向 gate 在不设置
   `MOUNTAIN_API_REQUEST_TIMEOUT_MS` 时正常 exit 0，同时 silent backend 仍由 checker 自身有界
   exit 1。可以使用大于后端单 endpoint 上限的请求 deadline 配合首个 timeout fail-fast，或等价的
   总体 deadline；不得删除 AbortController、依赖外层 `timeout`，也不得预热/伪造 probe cache。
2. 增加回归测试，证明一个合法但耗时接近 5 秒边界的响应不会被默认 deadline 错杀，并保留现有
   silent-server subprocess 的 `signal=null`、自身非零退出和清理断言。
3. 修正报告的 live gate 证据，并在 fresh 临时 data dir 上按报告命令（无 timeout override）重跑；
   保持既有路径脱敏和同源生命周期说明。

该轮返工只允许修改两个 checker 脚本、聚焦 checker 测试和交付报告；不得修改后端 probe、产品页面、
API/DTO、E2E 脚本、截图、manifest、`WEB-PARITY-004` 或 `WEB-WO-003`。复核命令：

```text
npm --prefix web-v2 test -- --run tests/contract-checker-exec.test.ts
npm --prefix web-v2 test -- --run
npm --prefix web-v2 run build
MOUNTAIN_API_BASE=http://127.0.0.1:<fresh-api-port> node web-v2/scripts/check-api-contract.mjs
git diff --check 0dbbf4e...HEAD
```

真实 API 必须由 fresh 临时 data dir 启动，不能用已有 probe cache 掩盖 5 秒竞态。上述三项已由
`51656c9` 完成并通过本文 Attempt 3 最终复核。

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

## Attempt 1 必须纠正（attempt 2 已完成）

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

## Attempt 1 有界返工范围（历史）

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

上述 attempt 1 范围已由 `0dbbf4e` 交付，后续 5 秒竞态也已由 `51656c9` 纠正并独立复核。
本 verdict 不修改任务状态、不合并，也不触碰 `WEB-PARITY-004` 或 `WEB-WO-003`。
