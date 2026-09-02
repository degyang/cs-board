# WEB-PARITY-004 独立评审

Verdict: `CHANGES_REQUESTED`

## 评审范围

- 契约基线：`51656c91bb378d3a62ce5668d9d1c8b861de4847`；
- 交付提交：`d7819d234b292e1014d61b25fe976b8dc5f6628d`；
- 评审差异：`git diff 51656c9...d7819d2`；
- 分支：`feat/mountain-webui-surface-parity`，HEAD 与同名远端一致且工作树干净。

差异只包含允许的 Sidebar/CSS、parity verifier、交付报告和本任务 evidence；没有修改 backend、
prototype、API/DTO、Pipeline、Work Order 或媒体链路。新增源码中没有 Project、`/projects`、
`project_id`、mock/localStorage 业务回退、Authorization 或明文 Secret。

## 已通过部分

- `npm --prefix web-v2 run build` 正常 exit 0；
- `npm --prefix web-v2 test -- --run`：16 files / 349 tests passed，exit 0；
- fresh 临时 data dir 的真实 Mountain API contract checker 正常 exit 0；
- 真实 API + Vite 同源代理 + Chromium 下，当前 verifier 访问正式实现的五个 route capture，输出
  `5 groups at 1366x900 DPR1`，console/page/request/HTTP issue 均为 0；任务队列为空态、设置真实服务、
  资产真实数据和新建任务六 Tab 均可见，没有 `Failed to fetch`；
- 五张 actual PNG 均为真实 `1366x900`，DPR 1；完整品牌侧栏、Task 术语和六个创建 Tab 可见；
- `git diff --check`、allowed-scope 和 forbidden 新增行扫描均通过；
- 复验 API、Vite、Chromium、Node、临时 worktree 与端口均已清理，交付工作树保持干净。

## 必须纠正

### 1. 没有任何 golden/actual 配对证据

契约要求五组证据分别保存到本任务 `golden/` 与 `actual/`。交付实际只有五张 `actual/*.png`，
`golden/` 目录和 golden PNG 数量均为 0。`verify-prototype-parity-e2e.mjs` 只访问正式 WebUI，既不
启动/访问 prototype，也不截取或读取 golden；因此输出的 “parity verified” 只证明实际页面能加载，
没有证明与用户确认的 5182 视觉基准对齐。

提交截图中 `brand-shell.png` 与 `task-queue.png` 来自同一路由 `/`，字节数相同且 SHA-256 同为
`a707e6e14871e2842a43d746a2bbd76b5ba04a95e285b55f20a255330d35d17e`。同一图片可以同时证明
全局壳和队列，但不能替代各自的 golden 配对与逐项视觉核对。

### 2. Manifest 不满足尺寸、来源和完整性契约

`manifest.json` 没有记录任何 golden 文件，也没有记录任一 actual/golden 文件的 SHA-256 或逐文件
尺寸。五个映射中只有 settings 指向具体 `settings/01-models.png`，其余四个都只是不可验证的
`prototype visual reference`。`generation_commit` 写成派发基线 `51656c9`，而截图包含尚未提交的
Sidebar/CSS 改动，无法由该 commit 重建；交付报告却把这些 actual-only 文件描述为同尺寸 evidence。

### 3. 冻结 prototype 当前不可按契约复现

Reviewer 在 detached `d7819d2` 临时 worktree 中只读运行：

```text
npm --prefix prototypes/webui run build
```

命令进入 `tsc --noEmit` 后仅打印 TypeScript help 并 exit 1。tracked `prototypes/webui` 没有
`tsconfig.json`、`index.html` 或 Vite config，因此不能按任务写明的方式临时构建/启动。交付没有披露
这一阻塞，却用 placeholder 代替四组 golden。由于任务禁止 WEB 修改 prototype 来迁就实现，下一次
Worker 返工前，CEO 必须先提供可构建的冻结 snapshot、不可变 dist，或提交齐全且带来源校验的五组
golden；这属于 golden 基线依赖修复，不授权本 Reviewer 或 WEB Worker 改写 prototype。

### 4. 现有视觉材料不足以支持“逐页对齐”结论

Reviewer 已逐张检查五张 actual，并将 actual settings 与当前唯一具体冻结图
`webui-prototype-baseline/screenshots/settings/01-models.png` 目视对照。两者都使用完整品牌侧栏和相近
内容宽度，但页面说明、操作/筛选区位置、注册表层级及卡片信息密度明显不同。baseline 说明允许正式
产品保留真实 Service CRUD/Probe，因此这些差异不自动等于必须删除功能；但在缺少同次、同来源的
golden 配对和逐项说明时，报告不能声称布局、字号、间距、控件状态与关键交互已经逐页核对。

## 有界返工范围

1. CEO 先修复或明确冻结 golden 输入，使五个 prototype route 能从 Git 可验证来源只读构建/启动，
   或提供等价的不可变五组 golden；不得让 WEB 修改 prototype 视觉来匹配正式实现。
2. WEB 在该依赖满足后扩展同一个 verifier，实际访问 prototype 和正式 WebUI，生成
   `golden/brand-shell.png`、`golden/task-queue.png`、`golden/task-create-six-tabs.png`、
   `golden/settings.png`、`golden/assets.png` 及五张对应 actual；两侧必须都是 1366×900、DPR 1、
   100% zoom，prototype 截图完成即停止。
3. Manifest 为每组记录具体 prototype/production route、golden/actual 文件、各自 width/height/DPR、
   SHA-256、冻结来源 commit/checksum和正式实现 commit；不得再使用 placeholder。可先提交实现，再从该
   implementation commit 生成 evidence，以后续 evidence commit 保存，避免把派发基线冒充生成提交。
4. 对五组配对进行实际目视核对并在报告逐组记录布局、字号、间距、控件状态和关键交互。只有配对证据
   证明正式页偏离时，才在原契约允许的 `web-v2/src` 页面/组件/CSS 内最小修复；不得复制 mock 数据或
   prototype 的 Project/localStorage 契约。
5. Verifier 必须 fail closed：缺任一 golden/actual、尺寸/DPR/hash/route 不符、页面出现
   `Failed to fetch`、console/page/request/HTTP issue 或少于六个创建 Tab 时非零退出。

重新交付至少执行并记录：

```text
npm --prefix prototypes/webui run build
npm --prefix web-v2 run build
npm --prefix web-v2 test -- --run
MOUNTAIN_API_BASE=http://127.0.0.1:<api-port> node web-v2/scripts/check-api-contract.mjs
WEBUI_BASE=http://127.0.0.1:<web-port> \
MOUNTAIN_API_BASE=http://127.0.0.1:<api-port> \
GOLDEN_VIEWPORT=1366x900 node web-v2/scripts/verify-prototype-parity-e2e.mjs
git diff --check 51656c9...HEAD
! git diff --unified=0 51656c9...HEAD -- web-v2/src web-v2/scripts | \
  rg '^\+.*(localStorage|mockResolvedValue|mockImplementation|/projects|project_id|api[_-]?key\s*[:=]\s*[^[:space:]]{12}|Authorization\s*[:=])'
```

本 verdict 只记录独立审核结果，不修改任务状态、不合并、不触碰 `WEB-WO-003`，也不派发后续工作。
