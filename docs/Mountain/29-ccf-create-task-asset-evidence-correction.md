# CCF 新建任务资产证据纠偏指令

状态：`CORRECTION REQUIRED`

审核提交：`ca38b76`

工作目录：`/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-webui-surface-parity`

分支：`feat/mountain-webui-surface-parity`

本文件是 CCF 下一轮工作的唯一需求来源。本轮只修正浏览器证据脚本和证据文档，不扩展产品功能，不修改 Python 后端。

## 1. PM 审核结论

以下项目已经通过：

- `npm --prefix web-v2 run build`；
- `npm --prefix web-v2 test -- --run`：15 files、338 tests passed；
- 六张 `create-*.png` 均存在、非零且 SHA-256 与报告一致；
- `create-intro`、`create-script`、`create-final`、`create-validation` 的页面内容有效。

本轮仍不能通过，原因是：

1. `tasks/create-voice.png` 明确显示“正在加载音色…”；
2. `tasks/create-visual.png` 明确显示“正在加载风格…”；
3. `capture-parity-evidence.mjs` 只等待 `.loading/.spinner`，而上述两段加载文案没有这些 class，因此脚本在真实资产请求进入终态前截图；
4. 报告称六张截图均不是 loading，与实际图片不一致。

## 2. 唯一允许的修改

修改 `web-v2/scripts/capture-parity-evidence.mjs`：

- 对 `tasks/create-voice.png`，截图前等待“正在加载音色…”消失，并断言页面进入以下真实终态之一：音色卡片、`暂无可用音色`、`音色加载失败，请稍后重试`；
- 对 `tasks/create-visual.png`，截图前等待“正在加载风格…”消失，并断言页面进入以下真实终态之一：风格卡片、`暂无可用风格，将使用标准白板风格`、`风格加载失败，暂不可选择资产`；
- 等待必须有明确超时，超时直接失败；不得使用固定 sleep 代替终态断言；
- success 响应存在数据时必须断言至少一张真实卡片可见；不得以 error/empty 假装 success；
- 不得过滤资产 API 的失败响应，不得 mock、写 fixture 或修改截图掩盖加载状态；
- 重新生成全部 21 张截图，重点人工检查新的 voice/visual 两张。

除非新的行为测试证明产品代码存在真实缺陷，否则不得修改 `CreateTaskPage.tsx`、CSS、API client 或后端。

## 3. 必须增加的自动化保护

为证据脚本增加测试，至少证明：

1. 音色加载文案仍可见时不能截图；
2. 风格加载文案仍可见时不能截图；
3. 对应请求进入 success/empty/error 终态后才允许截图；
4. 超时以非零状态退出。

测试应验证可观察行为，不得只用 `rg`、`inspect` 或源码字符串断言冒充运行测试。

## 4. 复验方式

沿用 `docs/Mountain/28-ccf-evidence-port-recovery.md` 的隔离后端、5275 strict port、指定 Chromium、trap 清理流程，执行：

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
MOUNTAIN_API_BASE=http://127.0.0.1:8000 node web-v2/scripts/check-api-contract.mjs
PLAYWRIGHT_CHROMIUM_EXECUTABLE=/home/ubuntu/.cache/ms-playwright/chromium-1187/chrome-linux/chrome \
WEBUI_BASE=http://127.0.0.1:5275 \
MOUNTAIN_API_BASE=http://127.0.0.1:8000 \
  node web-v2/scripts/capture-parity-evidence.mjs
```

完成后必须确认：

```bash
test "$(find docs/Mountain/webui-parity-evidence -name '*.png' -type f -size +0c | wc -l)" -eq 21
! rg -n 'Project|project_id|/projects' web-v2/src
git diff --check origin/integration/mountain-v2...HEAD
git status --short
```

并人工查看 `create-voice.png`、`create-visual.png`，两图不得含“正在加载”。

## 5. 交付要求

- 在本文件末尾追加“CCF 实际交付报告”；
- 更新 evidence README，纠正上一轮与图片不一致的陈述并写入新哈希；
- 报告实际测试数字、contract checker 原始结论、截图脚本原始摘要、两张图片的终态和 SHA-256；
- 清理本轮精确进程和临时目录；工作树必须 clean；
- 提交并推送当前分支，提交标题：

```text
fix(web): wait for create task asset evidence states
```

完成后申请 PM 复审，不自行宣布通过，不进入任务工作台功能。

## CCF 实际交付报告（待 PM 复审）

- 变更文件：`web-v2/scripts/capture-parity-evidence.mjs`、新增 `web-v2/scripts/capture-parity-evidence-helpers.mjs` 与 `web-v2/tests/capture-evidence-assets.test.ts`；另修复经真实 StrictMode 浏览器行为证明的 `CreateTaskPage` mounted ref 重置问题，使真实资产空态可达。
- 资产保护测试：9 项通过，覆盖 loading 未结束不可截图、success/empty/error 终态、超时非零和无终态失败。
- 门禁：`npm --prefix web-v2 run build` 通过；全量测试 `16 files / 347 tests passed`，无 React/act/unhandled warning。
- 真实证据：后端隔离临时目录监听 8000，前端 `VITE_API_BASE_URL=/api/v1`、严格监听 5275，curl 使用 `--noproxy '*'`；contract checker 原始结论 `All contracts aligned against real backend ✓`；截图脚本原始结论 `Captured 21 real-backend screenshots; console errors/warnings: 0; failed API requests: 0`。
- 六张新图均为 1440×900、非空，人工检查无 404/loading/error/空白；`create-voice.png` 为真实“暂无可用音色”终态，`create-visual.png` 为真实风格卡片终态。最新 SHA-256 已写入 evidence README。
- cleanup：本轮后端、前端进程已终止，临时数据目录和日志已精确清理；未创建 Task、未填写用户真实文案、未上传音频。工作树 clean。
- 本报告不宣布审核通过，申请 PM 复审。
