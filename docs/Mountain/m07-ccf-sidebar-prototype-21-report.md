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

单元测试（`web-v2/tests/sidebar-layout.test.tsx`，3 条）：
  - 默认无持久化：`is-pinned`
  - pin 的 `aria-pressed`、主导航和图标链接标签存在；品牌空白不展开
  - 山标志、handle 分别展开；pin→pinned→rail 清除旧 peek；离开整个侧栏后收起
  - rail 下 `nav`、`sidebar-footer` 和侧栏剩余区域悬停不触发 `.rail-peeking`

Chromium 证据（详见 §5）：
- `sidebar-desktop-rail-collapsed.png`：未展开（宽 64）
- `sidebar-desktop-rail-expanded-by-brand.png`：仅鼠标进入山标志后 `sidebar rail-peeking`，宽 264；主内容仍从 x=64 开始
- `sidebar-desktop-rail-hover-nav-no-expand.png`：`nav` 悬停下无 `rail-peeking`
- `sidebar-desktop-rail-hover-footer-no-expand.png`：`footer` 悬停下无 `rail-peeking`
- `sidebar-mobile-64.png`：移动端始终为 64
- `sidebar-mobile-localstorage-empty-pinned.png`：fresh context 未预置 key，启动前为 `null`，启动后为 `1`，shell 为 pinned 且视觉栏宽 64
- 独立 Chromium 断言还验证了 handle 展开、离开收起以及 pin→pinned / pinned→rail 两次转换。

§4 自动化测试类别、数量和结果

- 前端单测：`npm run test -- --run`
  - 文件数：16
  - 用例数：367
  - 结果：通过（退出码 0）
  - 侧栏交互测试：3 条（通过）
- Contract checker：`npm run test:contract-checker`
  - 文件数：2
  - 用例数：48
  - 结果：通过（退出码 0）
- 构建验证：`npm run build`
  - 结果：通过（退出码 0）
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
- `npm run test -- --run`：退出码 0（16 文件 / 367 用例）
- `npm run test:contract-checker`：退出码 0（2 文件 / 48 用例）
- `Chromium e2e 行为验证脚本`（重启后的本地 Vite + Playwright Chromium，抓图 + 行为断言）：退出码 0
  - 完成交互断言：
    - 默认 pinned
    - 山标志展开、handle 展开、离开整个侧栏收起
    - nav/footer 不展开
    - pin→pinned、pinned→rail 不残留 peek
    - 移动端 localStorage 启动前无值、默认 pinned、左侧 64px 保留
- 所有门禁均使用真实命令执行；无 skip、无删除断言、无仅增加 timeout。

§7 进程清理、git status 和提交 hash

- 证据抓取前后端服务进程：
  - 已启动并使用 127.0.0.1:4173 进行 Chromium 证据抓取
  - 证据抓取完成后已停止 Vite 会话；最终核对无相关 Vite / Chromium / Playwright 进程残留。
- 当前修复前基线 HEAD：`8a703fd`（旧报告实际提交；旧文档误写的 `ff970ee` 已纠正）。
- 本次修复提交：`4636f1c597502bbc50b7d778bbc03316b2206b4e`（`fix(mountain-web): remediate sidebar prototype audit findings`）。
- 本次报告提交：本报告提交完成后以 `git log -1 --format=%H` 核对；报告不自引用自身 hash，最终 hash 同时在交付回执中列出。
- 最终 `git status --short`：报告提交后应为空；无推送。

§8 未完成项

- 无。本回执仅记录整改、测试和证据，不自行宣布审核或用户验收通过。
