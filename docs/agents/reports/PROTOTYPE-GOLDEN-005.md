# PROTOTYPE-GOLDEN-005 交付报告

- Task / attempt: `PROTOTYPE-GOLDEN-005` / 2（返工：冻结不可变 capture）
- Branch: `feat/mountain-prototype-golden`
- Source baseline: `0f56e824c0d49ab5c090e7ea07086dc9d47f47a9`
- Implementation / evidence commit: `7db041b4e1d5627d0dbf96218f38eeebd313ae7f`

## 交付内容

恢复 `prototypes/webui` 的最小 Vite/TypeScript 运行外壳：`index.html`、`tsconfig.json`、
锁定的 Playwright 开发依赖和 `scripts/capture-golden.mjs`。没有改动原型的既有
`src/` 视觉 token、布局、文案或交互源码，也没有改动 `web-v2/`。

捕获器仅以 `127.0.0.1:5182` 启动本工作树的 production preview，固定 `1366x900`、DPR 1、
100% zoom，并在每一页监听 console error、pageerror、failed request 与 HTTP >=400。冻结仅注入到
Playwright 的 capture 页面：固定 `Date`，并在 document root 创建时禁用 CSS animation/transition，
不改写原型的视觉与交互源码。任一问题、尺寸或 hash 缺失都会以非零状态退出；finally 清理 Chromium、
Vite 与临时截图目录。

默认 `node prototypes/webui/scripts/capture-golden.mjs` 只将新截图写进临时目录，并与已冻结的五张 PNG
及 manifest 原始字节逐项比较；任何差异都会非零退出，绝不会覆写基准。只有显式
`node prototypes/webui/scripts/capture-golden.mjs --update` 才会生成/更新 golden 与 manifest。

`WEB-PARITY-004-manifest.json` 固定上述 Git source baseline，并明确历史 `/projects` 仅作
视觉映射（正式 Task 路由 `/tasks`），历史 `/create` 对应正式 `/tasks/new`；没有迁移其 Project
契约、mock 或 localStorage 行为。

## Golden 证据

| 组 | Prototype route | Golden | SHA-256 | Bytes |
| --- | --- | --- | --- | ---: |
| 品牌壳 | `/help` | `01-brand-shell.png` | `a33f02db0b429b3617a717279d926588cadd1c65debbe19c5c02a7c10836117a` | 173408 |
| 任务队列 | `/projects` | `02-task-queue.png` | `2d6f574ec828a2742747a4c767572d0a089797b9c464f9e529905c7b344b47f5` | 154796 |
| 六 Tab 新建任务映射 | `/create` | `03-create-six-tabs.png` | `993d4f8ee3d4490586c8f26e39d119366d67245a459e495d44a150a7c0bed545` | 87886 |
| 设置 | `/settings` | `04-settings.png` | `c4049516bb0e945e02b2ff6c1f3cd128186a02bd83e6001e2ce94de23c36ac3f` | 154049 |
| 资产 | `/assets` | `05-assets.png` | `0b42a9ab01306819137ae08343b04632b7b7b757db6e7dec592429488969b0c1` | 265580 |

所有 PNG 已用 `file` 核验为 `1366 x 900`、RGB PNG；manifest 逐项记录 route、文件、宽高、DPR、
SHA-256 与 bytes。浏览器四类问题计数均为 `0`。

## 门禁记录

| Command | Exit | Result |
| --- | ---: | --- |
| `npm --prefix prototypes/webui install` | 0 | 安装完整；npm 报告 5 个既有依赖审计项（3 moderate、2 high），未执行超出范围的 `audit fix --force`。 |
| `npm --prefix prototypes/webui run build` | 0 | `tsc --noEmit` 和 `vite build` 均完成。 |
| `node prototypes/webui/scripts/capture-golden.mjs` | 0 | 真实 Playwright Chromium 访问 5 个 prototype route，并 fail-closed 复验冻结 PNG/manifest。 |
| `node prototypes/webui/scripts/capture-golden.mjs --update` | 0 | 显式重建冻结基准（默认命令不会写入）。 |
| 连续两次默认 capture + `diff` / `cmp` | 0 | 五个 SHA-256 列表与 manifest 原始字节完全一致。 |
| `ss -ltn '( sport = :5182 )'` cleanup check | 0 | 捕获器退出后端口未监听；临时 Vite/Chromium 已清理。 |
| `git diff --check 0f56e82...HEAD` | 0 | 无空白错误。 |
| `! git diff --name-only 0f56e82...HEAD \| rg '^web-v2/'` | 0 | 没有 `web-v2/` 改动。 |

## Reviewer handoff

请独立执行 build 和 capture；抽查任意 PNG 的尺寸/SHA-256 与
`docs/Mountain/webui-prototype-baseline/WEB-PARITY-004-manifest.json`，并确认捕获器使用的仅是
`prototypes/webui` loopback preview。此交付不解除 `WEB-PARITY-004` blocker，等待独立审核。
