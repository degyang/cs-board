§1 执行基线与变更文件

基线依据（仅阅读，不修改）：
- docs/Mountain/webui-prototype-baseline/source/README.md（章节：侧边栏展开 / 收起交互）
- docs/Mountain/webui-prototype-baseline/source/src/components/layout/Sidebar.tsx（pin / rail / peek 参考）
- docs/Mountain/webui-prototype-baseline/source/src/styles/app.css（侧边导航栏 Sidebar、图标栏模式 Rail、图钉按钮 Pin、展开触发条 Rail Handle、响应式）

本次变更文件：
- web-v2/src/components/layout/AppShell.tsx
- web-v2/src/components/layout/Sidebar.tsx
- web-v2/src/styles/app.css
- web-v2/tests/sidebar-layout.test.tsx（新增）
- docs/Mountain/evidence/ccf-sidebar-21/*.png / summary.json / sha256.txt / chromium-version.txt（新增证据）
- 本报告：docs/Mountain/m07-ccf-sidebar-prototype-21-report.md

不改动范围（已核对）：后端、任务创建业务、工作台、资产/设置业务逻辑及任何原型基准文件。

§2 原型差异逐项关闭清单

本轮针对审核问题逐项关闭：

1) 触发热区过宽：已移除品牌容器级展开事件，只有 `.brand-mark`（山）和 `.rail-handle` 两个可见控件绑定 `expand`；品牌区剩余空白、导航、footer、运行入口不触发展开。

2) pin / peek 状态泄漏：pin 按钮切换时同步清除 `peek`，从 pinned 再取消钉住时从干净 64px rail 开始；`onMouseLeave` 仍是整个侧栏的收起边界。

3) 图标栏可访问性不足：补齐 `aside/nav` 标签、pin 的 `aria-pressed` / `aria-label`、图标链接的 `aria-label` / `title`，山标志和 handle 使用真实 button 语义并提供聚焦展开及可见焦点。

4) 移动端默认值证据不足：新增真实 Chromium fresh context；应用启动前观测 `localStorage[mountain.ui.sidebarPinned] === null`，随后验证默认 pinned 且响应式仍保留左侧 64px。

其余原型差异保持关闭：rail 默认 64px；peek 为 264px fixed 浮层，不挤压主内容；rail 保留山标志、导航图标和运行入口；正式 Task 路由 `/tasks`、`/tasks/new`、`/tasks/:taskId` 与 `fetchTasks` 动态运行数据未改为原型旧 Project/fixture。

§3 pin / rail / peek 行为证据

自动化测试（`web-v2/tests/sidebar-layout.test.tsx`，5 条）补齐四类此前未验证行为，并保留原有默认态/负向断言：
  - 精确触发区：品牌空白不展开，山标志和 handle 可通过鼠标及键盘 focus 展开。
  - 侧栏内移动：从触发控件移动到 nav/footer 时 peek 保持，只有离开整个 aside 才收起。
  - pin 状态机：peek→pinned、pinned→rail 均清除旧 peek，并验证 localStorage `1` / `0` 持久化。
  - rail 内容与正式数据：图标链接具备可访问标签，运行入口使用动态任务 `task-001` 的正式 `/tasks/task-001` 路由。
  - 卸载保护：Sidebar 卸载时 abort 动态运行任务请求；晚到响应不会更新已卸载组件。

Chromium 证据（详见 §5）：
- `sidebar-desktop-rail-collapsed.png`：未展开（宽 64）
- `sidebar-desktop-rail-expanded-by-brand.png`：仅鼠标进入山标志后 `sidebar rail-peeking`，宽 264；主内容仍从 x=64 开始
- `sidebar-desktop-rail-hover-nav-no-expand.png`：`nav` 悬停下无 `rail-peeking`
- `sidebar-desktop-rail-hover-footer-no-expand.png`：`footer` 悬停下无 `rail-peeking`
- `sidebar-mobile-64.png`：移动端始终为 64
- `sidebar-mobile-localstorage-empty-pinned.png`：fresh context 未预置 key，启动前为 `null`，启动后为 `1`，shell 为 pinned 且视觉栏宽 64
- 既有截图保持不变；本轮新增行为由上述自动化测试证明，不以单张截图替代负向交互验证。

§4 自动化测试类别、数量和结果

- 前端单测：`npm run test -- --run`
  - 文件数：16
  - 用例数：369
  - 结果：通过（退出码 0）
  - 侧栏交互测试：5 条（通过，无 warning）
- Contract checker：`npm run test:contract-checker`
  - 文件数：2
  - 用例数：48
  - 结果：通过（退出码 0）
- 构建验证：`npm run build`
  - 结果：通过（退出码 0）
- 本轮新增测试类别：焦点可访问性、父级 hover 边界、pin 持久化、运行入口正式路由、请求 AbortController 卸载保护。
- 禁止项核对：未 skip、未删除断言、未仅增加 timeout。

§5 Chromium 浏览器证据、尺寸和 SHA-256

- Chromium 版本：`151.0.7922.34`（由 Playwright Chromium 实际运行）
- 证据文件（sidebar 截图尺寸：宽×高）与 SHA-256：
  - `sidebar-desktop-pinned.png`（264×900）  
    `2c0f213a80b01a27f72211f6c982ddb6f47a1ed56ca69fa3da92189bc65f1e42`
  - `sidebar-desktop-rail-collapsed.png`（64×900）  
    `c0d6f3942ea1c24c049cc843287056d909e101abcedc94aabac2922c4989a802`
  - `sidebar-desktop-rail-expanded-by-brand.png`（264×900）  
    `c5b0d0237d0b75b8c89b0500f86faa7d89cf18c1f897941f6dd1ebc138a4fa29`
  - `sidebar-desktop-rail-hover-nav-no-expand.png`（64×900）  
    `c0d6f3942ea1c24c049cc843287056d909e101abcedc94aabac2922c4989a802`
  - `sidebar-desktop-rail-hover-footer-no-expand.png`（64×900）  
    `c4357559a81870a428158086bfd8e2c6c28a05edfd4621ae70d48952be3fa854`
  - `sidebar-mobile-64.png`（64×844）  
    `9cbd2af3b378f2bec0768edf5b7615b11e32ffbcc7b7de71498c3692d3dee740`
  - `sidebar-mobile-localstorage-empty-pinned.png`（64×844）
    `e5c5f36063dd440b69a63356bbb0564cd19f9cf8ca041dd54bc2bafec6cb0f37`

附：`docs/Mountain/evidence/ccf-sidebar-21/sha256.txt`、`summary.json`、各 PNG 的同名 JSON 几何记录及 `mobile-localstorage-empty.json`。

§6 全部门禁及正常退出结果

- `npm run build`：退出码 0
- `npm run test -- --run`：退出码 0（16 文件 / 369 用例）
- `npm run test:contract-checker`：退出码 0（2 文件 / 48 用例）
- 既有真实 Chromium 门禁证据沿用且未修改；本轮不重新制作截图。
  - 交互证据仍覆盖默认 pinned、山标志/handle 展开、nav/footer 负向、移动端无值 localStorage。
  - 新增自动化覆盖侧栏内移动保持 peek、pin 持久化与 pin/rail 转换、Sidebar 卸载 abort 请求及晚到响应保护。
- 所有门禁均使用真实命令执行；无 skip、无删除断言、无仅增加 timeout。

§7 进程清理、git status 和提交 hash

- 证据抓取前后端服务进程：
  - 本轮未启动浏览器服务；沿用已有 Chromium 证据，测试与 build 均为本地执行。
  - 最终核对无 Vite / Chromium / Playwright 残留进程。
- 上一轮修复提交：`4636f1c597502bbc50b7d778bbc03316b2206b4e`。
- 上一轮报告提交：`9e11b674afa36551106debbf848d549b06cd10fd`。
- 本轮修复提交：`642124e34474f7cabdb72d9095c1267cb069b381`（`fix(mountain-web): verify sidebar state and abort runtime request`）。
- 本轮报告提交：本报告提交完成后以 `git log -1 --format=%H` 核对；报告不自引用自身 hash，最终 hash 在交付回执列出。
- 最终 `git status --short`：报告提交后为空；只本地提交，不推送。

§8 未完成项

- 无。本轮只补齐自动化行为和请求卸载保护，不自行宣布审核或用户验收通过。
