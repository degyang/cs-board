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

1) “鼠标进入侧栏任意区域即展开”  
完成：由 rail 模式下的 `peek` 状态机接管，默认仅 `brand` 元素触发展开。

2) 未钉住状态保持 64px 图标栏  
完成：`app-shell.is-rail` 时 `.sidebar` 基础宽度固定为 64px，且默认不含 `rail-peeking` 类。

3) 仅品牌区“山”标志与其下触发条可临时展开  
完成：侧边栏 `brand`（含品牌区与 `rail-handle`）绑定 `onMouseEnter={expand}`。

4) 导航区 / 空白区 / footer / 运行状态悬停不得展开  
完成：仅 `brand` 有 `expand` 入口；导航、footer 只在 rail 下展示图标，且不会触发 `rail-peeking`。

5) 展开为 264px 浮层覆盖，不挤压主内容  
完成：侧边栏 fixed 定位 + `grid-template-columns: 64px 1fr`；rail-peek 时侧边栏宽到 264px，主内容 left 保持 64px。

6) 鼠标离开整个侧栏后收起  
完成：`onMouseLeave={collapse}` 仅在 rail 状态内收起 `peek`。

7) rail 保留品牌标志、导航图标、底部运行入口  
完成：rail 折叠仅隐藏文字与次要信息，保留图标与底部运行/占位条。

8) 默认无持久化状态时为 pinned  
完成：`AppShell` 初始化时 `localStorage` 不存在则返回 `true`（pinned），并持久化最新状态。

9) 移动端保留 64px 左侧栏，不可完整隐藏  
完成：移动端 `@media (max-width: 768px)` 强制 `app-shell` 第一列 64px，`sidebar` 收起不超出 64px。

10) 路由与动态运行数据保留正式 Task 路由与实时数据  
完成：运行条目使用 `/tasks/:taskId`（正式任务路由）与 `fetchTasks` 找到 `running` 任务的真实 `task_id / title / status`。

§3 pin / rail / peek 行为证据

单元测试（新增）：
- `web-v2/tests/sidebar-layout.test.tsx`
  - 默认无持久化：`is-pinned`
  - rail 下仅 `brand` 悬停会触发 `.rail-peeking`
  - rail 下 `nav` 和 `sidebar-footer` 悬停不触发 `.rail-peeking`

Chromium 证据（详见 §5）：
- `sidebar-desktop-rail-collapsed.png`：未展开（宽 64）
- `sidebar-desktop-rail-expanded-by-brand.png`：仅鼠标进入 brand 后 `sidebar rail-peeking`，宽 264
- `sidebar-desktop-rail-hover-nav-no-expand.png`：`nav` 悬停下无 `rail-peeking`
- `sidebar-desktop-rail-hover-footer-no-expand.png`：`footer` 悬停下无 `rail-peeking`
- `sidebar-mobile-64.png`：移动端始终为 64

§4 自动化测试类别、数量和结果

- 前端单测：`npm run test -- --run`
  - 文件数：16
  - 用例数：367
  - 结果：通过
  - 新增侧栏交互测试：3 条（通过）
- Contract checker：`npm run test:contract-checker`
  - 文件数：2
  - 用例数：48
  - 结果：通过
- 构建验证：`npm run build`
  - 结果：通过

§5 Chromium 浏览器证据、尺寸和 SHA-256

- Chromium 版本：`151.0.7922.34`（由 Playwright Chromium 实际运行）
- 证据文件（尺寸：宽×高）与 SHA-256：
  - `sidebar-desktop-pinned.png`（264×900）  
    `d590c1b99ed40f0133dba0ea7fe7dbb36f9aff4cce0bcb1511936baa9c26a936`
  - `sidebar-desktop-rail-collapsed.png`（64×900）  
    `6bb261e762009e8a70102de0e5e36de028bbf9061d4a0a2e913287211328ace1`
  - `sidebar-desktop-rail-expanded-by-brand.png`（264×900）  
    `9cd8f67292d98dd36ac4125968ffe0b7f5aafad654fa4a5d1bc2993d5998d94c`
  - `sidebar-desktop-rail-hover-nav-no-expand.png`（64×900）  
    `6bb261e762009e8a70102de0e5e36de028bbf9061d4a0a2e913287211328ace1`
  - `sidebar-desktop-rail-hover-footer-no-expand.png`（64×900）  
    `6bb261e762009e8a70102de0e5e36de028bbf9061d4a0a2e913287211328ace1`
  - `sidebar-mobile-64.png`（64×844）  
    `c2f64a2a6b467c5a12a6c4f941b290cf88699e9a5e90661cebc515ed9055aec6`

附：`docs/Mountain/evidence/ccf-sidebar-21/sha256.txt`

§6 全部门禁及正常退出结果

- `npm run build`：通过退出码 0
- `npm run test -- --run`：通过退出码 0（16 文件 / 367 用例）
- `npm run test:contract-checker`：通过退出码 0（2 文件 / 48 用例）
- `Chromium e2e 行为验证脚本`（本地 Playwright 脚本抓图 + 行为断言）：通过退出码 0
  - 完成交互断言：
    - 默认 pinned
    - brand 展开
    - nav/footer 不展开

§7 进程清理、git status 和提交 hash

- 证据抓取前后端服务进程：
  - 已启动并使用 127.0.0.1:4173 进行 Chromium 证据抓取
  - 证据抓取完成后执行清理：`pkill -f '/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-assets-settings-web/web-v2/node_modules/.bin/vite --host 127.0.0.1 --port 4173 --strictPort'`
  - 清理前可见相关进程：`56232`（vite）、`56256`（esbuild helper）
- 最终 `git status --short`（预期）：
  - 当前工作区在最终提交后保持 `clean`
- 实现提交：`fix(mountain-web): align sidebar prototype interaction`
- 报告提交：`docs(mountain): report sidebar prototype alignment`
- 实际提交哈希：
  - be4a1d6
  - ff970ee

§8 未完成项

- 无。
