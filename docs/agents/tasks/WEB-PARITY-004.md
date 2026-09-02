# WEB-PARITY-004：WebUI 原型逐页对齐审计与修复

- Owner: WEB
- Status: BACKLOG
- Priority: P0
- Depends on: `WEB-INTAKE-003=APPROVED`
- Worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-webui-surface-parity`
- Branch: dispatch 时由 PM 固定
- Base commit: dispatch 时由 PM 固定

## Goal

以 `docs/Mountain/webui-prototype-baseline` 为唯一视觉与交互基准，独立审计并修复当前 WebUI。当前
`127.0.0.1:5181` 由旧 `feat/mountain-assets-settings-web@c221947` 提供，实测仍是图标 rail、单页表单，
且任务队列、设置、资产页显示 `Failed to fetch`；交付必须恢复原型的完整品牌侧栏、六 Tab 和统一内容
层级，并让这些页面在真实 Mountain API 下进入成功或明确空态。

## Allowed surfaces

- `web-v2/src` 中与品牌侧栏、路由壳、任务创建六 Tab、任务队列、设置、资产页直接相关的页面、组件与样式；
- `web-v2/scripts`、`web-v2/tests` 中聚焦原型对齐、真实 API 和浏览器证据的自动化；
- `docs/Mountain/webui-parity-evidence` 下本任务的逐页截图、尺寸/hash manifest；
- `docs/agents/reports/WEB-PARITY-004.md`。

## Forbidden surfaces

- Python/backend、API DTO、Pipeline、Stage Work Order、媒体链路；
- 复制原型中的 mock 数据、localStorage 业务状态或以静态成功态掩盖真实 API 失败；
- 明文 Secret、Authorization、完整用户文案、绝对素材路径进入页面、日志、截图或仓库；
- 顺手实现 `WEB-WO-003`、重做未被原型基准要求的信息架构或新增第二套 WebUI。

## Acceptance

1. 原型基准与实现证据使用完全相同的 CSS viewport、设备比例和浏览器缩放；DPR 固定为 1，逐页 manifest
   记录宽高、页面 URL、截图 hash 和对应原型引用，禁止靠裁切或缩放伪造同尺寸；
2. 全局壳与原型一致呈现完整品牌侧栏、导航分组、页面标题/说明/操作区和统一内容层级，不退回纯图标 rail；
3. 新建任务页按原型提供六个可访问 Tab，真实输入可跨 Tab 保存和回读，不改 `WEB-INTAKE-003` 已冻结 DTO；
4. 任务队列、设置、资产页使用真实 Mountain API；无数据时显示明确空态，API 失败时显示可诊断错误，验收运行中
   不得出现 `Failed to fetch`、console error、pageerror、failed request 或 HTTP >=400；
5. 至少提交品牌壳、新建任务六 Tab、任务队列、设置、资产五组同尺寸真实浏览器截图；逐页核对布局、字号、
   间距、控件状态、响应式行为和关键交互，不以文件存在代替视觉检查；
6. 自动化证明数据来自真实 API，源码和测试不存在新增 mock/localStorage 业务回退、明文 Secret 或 Work Order 请求；
7. 保留当前 intake 行为和安全边界，不进入 Start、Pipeline 或 Work Order 页面。

## Gates

```bash
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
MOUNTAIN_API_BASE=http://127.0.0.1:<api-port> node web-v2/scripts/check-api-contract.mjs
WEBUI_BASE=http://127.0.0.1:<web-port> \
MOUNTAIN_API_BASE=http://127.0.0.1:<api-port> \
node web-v2/scripts/verify-prototype-parity-e2e.mjs
git diff --check <dispatch-base>...HEAD
! git diff --unified=0 <dispatch-base>...HEAD -- web-v2/src web-v2/scripts | \
  rg '^\+.*(localStorage|mockResolvedValue|mockImplementation|api[_-]?key\s*[:=]\s*[^[:space:]]{12}|Authorization\s*[:=])'
```

## Stop condition

`WEB-INTAKE-003` 未获独立审核批准时不得派发。完成后提交并推送当前 WEB 分支，报告列出逐页
baseline/current 同尺寸截图、manifest、真实 API 终态、浏览器问题计数和全部门禁结果；置为
`REVIEW_READY` 并通知 PM。不得领取 `WEB-WO-003`。
