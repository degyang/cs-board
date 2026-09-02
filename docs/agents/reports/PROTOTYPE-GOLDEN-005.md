# PROTOTYPE-GOLDEN-005 交付报告

- Task / attempt: `PROTOTYPE-GOLDEN-005` / 1（初次）
- Branch: `feat/mountain-prototype-golden`
- Source baseline: `0f56e824c0d49ab5c090e7ea07086dc9d47f47a9`
- Delivery commit: `3c537725bb06ce2b2c4ecb01313ca2f034f24253`

## 交付内容

恢复 `prototypes/webui` 的最小 Vite/TypeScript 运行外壳：`index.html`、`tsconfig.json`、
锁定的 Playwright 开发依赖和 `scripts/capture-golden.mjs`。没有改动原型的既有
`src/` 视觉 token、布局、文案或交互源码，也没有改动 `web-v2/`。

捕获器仅以 `127.0.0.1:5182` 启动本工作树的 production preview，固定 `1366x900`、DPR 1、
100% zoom，并在每一页监听 console error、pageerror、failed request 与 HTTP >=400。任一
问题、尺寸或 hash 缺失都会以非零状态退出；finally 清理 Chromium 和 Vite 临时服务。

`WEB-PARITY-004-manifest.json` 固定上述 Git source baseline，并明确历史 `/projects` 仅作
视觉映射（正式 Task 路由 `/tasks`），历史 `/create` 对应正式 `/tasks/new`；没有迁移其 Project
契约、mock 或 localStorage 行为。

## Golden 证据

| 组 | Prototype route | Golden | SHA-256 | Bytes |
| --- | --- | --- | --- | ---: |
| 品牌壳 | `/help` | `01-brand-shell.png` | `068e8a97191abbbc65706ff8c96203f243b44428d1ff62f2b610e52cf6ad9782` | 173414 |
| 任务队列 | `/projects` | `02-task-queue.png` | `519cc468f792c2b5f8a23ecab5b8ef3e1e695c1c5c3ffd08f0ac7b22dc509318` | 154789 |
| 六 Tab 新建任务映射 | `/create` | `03-create-six-tabs.png` | `1e5c5e24188126c4f2e1fd80e7b6a79941e048b77b459f805a7a807caf04cc0e` | 87880 |
| 设置 | `/settings` | `04-settings.png` | `e786d32f22395dac4f5691a40e97a257bb08de814f353ca366f94af3b6b58ff1` | 154046 |
| 资产 | `/assets` | `05-assets.png` | `c5adc17f6ac7fb8ea003be4b47c9a9cf3f343c438a86e8bd83f2d15405db3261` | 265580 |

所有 PNG 已用 `file` 核验为 `1366 x 900`、RGB PNG；manifest 逐项记录 route、文件、宽高、DPR、
SHA-256 与 bytes。浏览器四类问题计数均为 `0`。

## 门禁记录

| Command | Exit | Result |
| --- | ---: | --- |
| `npm --prefix prototypes/webui install` | 0 | 安装完整；npm 报告 5 个既有依赖审计项（3 moderate、2 high），未执行超出范围的 `audit fix --force`。 |
| `npm --prefix prototypes/webui run build` | 0 | `tsc --noEmit` 和 `vite build` 均完成。 |
| `node prototypes/webui/scripts/capture-golden.mjs` | 0 | 真实 Playwright Chromium 访问 5 个 prototype route，写入五张 golden 与 manifest。 |
| `ss -ltn '( sport = :5182 )'` cleanup check | 0 | 捕获器退出后端口未监听；临时 Vite/Chromium 已清理。 |
| `git diff --check 0f56e82...HEAD` | 0 | 无空白错误。 |
| `! git diff --name-only 0f56e82...HEAD \| rg '^web-v2/'` | 0 | 没有 `web-v2/` 改动。 |

## Reviewer handoff

请独立执行 build 和 capture；抽查任意 PNG 的尺寸/SHA-256 与
`docs/Mountain/webui-prototype-baseline/WEB-PARITY-004-manifest.json`，并确认捕获器使用的仅是
`prototypes/webui` loopback preview。此交付不解除 `WEB-PARITY-004` blocker，等待独立审核。
