# WEB-PARITY-004：WebUI 原型逐页对齐审计与修复

- Owner: WEB
- Status: CHANGES_REQUESTED
- Priority: P0
- Depends on: `WEB-INTAKE-003=APPROVED`
- Worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-webui-surface-parity`
- Branch: `feat/mountain-webui-surface-parity`
- Base commit: `51656c91bb378d3a62ce5668d9d1c8b861de4847`

## Goal

以用户刚在 `127.0.0.1:5182` 确认的只读 prototype dist 为正式 WebUI 的视觉、页面结构和交互层级
golden，结合冻结说明 `docs/Mountain/webui-prototype-baseline` 独立审计并修复当前 WebUI。旧
`127.0.0.1:5181` 的 `feat/mountain-assets-settings-web@c221947` 实测仍是图标 rail、单页表单，且任务
队列、设置、资产页显示 `Failed to fetch`；交付必须恢复 golden 的完整品牌侧栏、六 Tab 和统一内容
层级，并让这些页面在真实 Mountain API 下进入成功或明确空态。

## Authoritative golden baseline

- 视觉与交互 golden 是刚才 5182 展示的只读 prototype dist，不是 5181 旧实现，也不是 worker 自行重画；
- 5182 与 5181 均已停止，不是运行依赖。验收时只允许从冻结的 `prototypes/webui` / baseline 快照临时
  构建并以只读方式启动 prototype，先生成 golden 截图，截图完成立即停止；不得修改 prototype 来迁就实现；
- golden 与正式实现均以 `1366x900` CSS viewport、DPR 1、100% zoom 截图；每一页面必须一一配对，
  保存到本任务 evidence 的 `golden/` 与 `actual/`，manifest 记录路由映射、尺寸、hash 和生成 commit；
- prototype 中历史 Project `/projects` 入口只用于视觉映射。正式实现一律使用 Task 术语、`/tasks`、
  `/tasks/new`、`/tasks/{task_id}` 与真实 `/api/v1`，禁止迁移旧路由或旧 DTO。

## Allowed surfaces

- `web-v2/src` 中与品牌侧栏、路由壳、任务创建六 Tab、任务队列、设置、资产页直接相关的页面、组件与样式；
- `web-v2/scripts`、`web-v2/tests` 中聚焦原型对齐、真实 API 和浏览器证据的自动化；
- `docs/Mountain/webui-parity-evidence` 下本任务的逐页截图、尺寸/hash manifest；
- `docs/agents/reports/WEB-PARITY-004.md`。

## Forbidden surfaces

- Python/backend、API DTO、Pipeline、Stage Work Order、媒体链路；
- 复制原型中的 mock 数据、localStorage 业务状态或以静态成功态掩盖真实 API 失败；
- 迁移 prototype 的 `/projects` 契约、Project 术语、fixture 请求或 mock client；
- 明文 Secret、Authorization、完整用户文案、绝对素材路径进入页面、日志、截图或仓库；
- 顺手实现 `WEB-WO-003`、重做未被原型基准要求的信息架构或新增第二套 WebUI。

## Acceptance

1. 5182 prototype golden 与正式实现证据均为 `1366x900`、DPR 1、100% zoom；逐页 manifest 记录
   golden/actual 文件、路由映射、生成 commit 与 hash，禁止靠裁切、缩放或修改 golden 伪造同尺寸；
2. 全局壳与原型一致呈现完整品牌侧栏、导航分组、页面标题/说明/操作区和统一内容层级，不退回纯图标 rail；
3. 新建任务页按原型提供六个可访问 Tab，真实输入可跨 Tab 保存和回读，不改 `WEB-INTAKE-003` 已冻结 DTO；
4. 任务队列、设置、资产页使用真实 Mountain API；无数据时显示明确空态，API 失败时显示可诊断错误，验收运行中
   不得出现 `Failed to fetch`、console error、pageerror、failed request 或 HTTP >=400；
5. 至少提交品牌壳、新建任务六 Tab、任务队列、设置、资产五组同尺寸真实浏览器截图；逐页核对布局、字号、
   间距、控件状态、响应式行为和关键交互，不以文件存在代替视觉检查；
6. 自动化证明数据来自真实 `/api/v1`，正式源码和测试不存在新增 mock/localStorage 业务回退、`/projects`
   旧契约、Project 术语、明文 Secret 或 Work Order 请求；
7. 保留当前 intake 行为和安全边界，不进入 Start、Pipeline 或 Work Order 页面。

## Gates

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
MOUNTAIN_API_BASE=http://127.0.0.1:<api-port> node web-v2/scripts/check-api-contract.mjs
WEBUI_BASE=http://127.0.0.1:<web-port> \
MOUNTAIN_API_BASE=http://127.0.0.1:<api-port> \
GOLDEN_VIEWPORT=1366x900 node web-v2/scripts/verify-prototype-parity-e2e.mjs
git diff --check <dispatch-base>...HEAD
! git diff --unified=0 <dispatch-base>...HEAD -- web-v2/src web-v2/scripts | \
  rg '^\+.*(localStorage|mockResolvedValue|mockImplementation|/projects|project_id|api[_-]?key\s*[:=]\s*[^[:space:]]{12}|Authorization\s*[:=])'
```

## Stop condition

`WEB-INTAKE-003` 未获独立审核批准时不得派发。完成后提交并推送当前 WEB 分支，报告列出逐页
5182 golden/正式实现同尺寸截图、manifest、真实 API 终态、浏览器问题计数和全部门禁结果；置为
`REVIEW_READY` 并通知 PM。不得领取 `WEB-WO-003`。

## Dispatch

- Attempt: 1（初次）
- Coordination decision: `090de4c`
- Dispatch state: `DISPATCHED`

Worker 仅执行本契约并在提交、推送、通知 PM 后停止；不得等待或领取同 Owner 的 `WEB-WO-003`。

## Review handoff

- Delivery: `d7819d234b292e1014d61b25fe976b8dc5f6628d`
- Report: `docs/agents/reports/WEB-PARITY-004.md`
- State: `REVIEW_READY`

Worker 分支已推送并与远端一致；本节只记录交接，不代表 PM、用户、发布或合并批准。

## Independent review decision

- Review: `docs/agents/reviews/WEB-PARITY-004.md`
- Review commit: `d069a34`
- Verdict: `CHANGES_REQUESTED`
- CEO state: `BLOCKED`

交付 `d7819d2` 的正式 WebUI build、349 tests、真实 API、actual 浏览器证据和范围扫描通过，但没有任何
golden PNG、逐文件 hash 或完整可复现 route mapping；verifier 也没有打开冻结 prototype。

### Verified golden-input blocker

Git 跟踪的 `prototypes/webui` 与 `docs/Mountain/webui-prototype-baseline/source` 均缺少可构建所需的
`tsconfig.json`、`index.html` 和 Vite config；当前冻结截图只覆盖 settings，不能组成契约要求的品牌壳、
任务队列、六 Tab 创建页、设置和资产五组 golden。因此 attempt 2 暂不派发给 WEB。

CEO 必须先提供以下任一 Git 可验证、不可变输入，才能解除阻塞并派发同一任务的有界纠正：

1. 可只读构建/启动且来源 commit 固定的完整 prototype snapshot；
2. 来源 checksum 固定的不可变 prototype dist；
3. 五组完整 `1366x900`、DPR 1、100% zoom golden 及来源/hash manifest。

解除阻塞后，WEB 只执行独立评审中的 golden/actual 配对、fail-closed verifier、manifest 与逐页目视报告
纠正；不得修改 prototype 视觉、复制 mock/localStorage/Project 契约，或领取 `WEB-WO-003`。

## Attempt 2 dispatch

- Golden dependency: `PROTOTYPE-GOLDEN-005@b4287d9=APPROVED`
- Golden review: `2dd4e99`
- Coordination state: `DISPATCHED`
- Cycle: 返工
- Attempt: 2

仅执行既有独立评审列出的五组 golden/actual 配对、manifest、fail-closed verifier 和必要的正式 WebUI
最小修正；不得修改 prototype、backend、Work Order 或领取 `WEB-WO-003`。

## Attempt 2 review handoff

- Delivery: `cdda8725e7c23ad8dfa9b3d6548d8d7e4323bd1c`
- Report head: `eadf15a1f8d706999660d2a42c9ccb4aae579101`
- Report: `docs/agents/reports/WEB-PARITY-004.md`
- State: `REVIEW_READY`

WEB 分支已推送且报告记录全部契约门禁正常退出；本节只登记独立审核入口，不代表 CEO、用户、发布或
合并批准。Reviewer 必须以 attempt 2 交付与已批准 golden 为边界独立复核。

## Attempt 2 independent review

- Review: `docs/agents/reviews/WEB-PARITY-004.md`
- Review commit: `de37fe1`
- Verdict: `CHANGES_REQUESTED`

五组 golden/actual、hash/manifest、视觉抽查、build、349 tests 与 diff check 均通过；唯一失败是 verifier
源码新增 legacy `/projects` 字面量，触发既定 forbidden-pattern gate。attempt 3 只允许从 verifier 源码
移除该旧契约引用，同时把已批准 prototype-to-Task 视觉映射保留在 evidence/manifest；重新运行全部原
门禁。不得修改 prototype、backend、Work Order 或领取 `WEB-WO-003`。

- Attempt 3 dispatch state: not dispatched
