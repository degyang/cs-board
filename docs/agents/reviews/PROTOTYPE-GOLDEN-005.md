# PROTOTYPE-GOLDEN-005 独立评审（attempt 2）

Verdict: `APPROVED`

## 评审范围

- 契约基线：`0f56e824c0d49ab5c090e7ea07086dc9d47a9`；
- 审核交付：`b4287d9ccdd12dc70a07314ab9b6aa377aa4fc17`；实现提交：
  `7db041b4e1d5627d0dbf96218f38eeebd313ae7f`；
- Owner worktree / branch：`/mnt/d/workstation/projects/cs-board-prototype-golden` /
  `feat/mountain-prototype-golden`，审核时工作树干净并与远端一致（ahead/behind `0/0`）。

`git diff --check 0f56e82...b4287d9` 通过，且 diff 中没有 `web-v2/`。累计变更限于允许的
prototype 构建/捕获外壳、五张 golden、manifest 与交付报告；`prototypes/webui/src/` 没有改动，未触及
backend、DTO、Pipeline、媒体链路或 Dashboard。

## 独立复现

在 Owner worktree 中使用项目 Node 工具链（Node `v24.15.0`、npm `11.12.1`）执行：

```text
npm --prefix prototypes/webui install
exit 0; up to date（npm 报告既有 5 项 audit 风险，未执行越界修复）

npm --prefix prototypes/webui run build
exit 0; tsc --noEmit + Vite build completed（72 modules）

node prototypes/webui/scripts/capture-golden.mjs
exit 0; verified 5 frozen browser goldens from 0f56e824...

node prototypes/webui/scripts/capture-golden.mjs
exit 0; verified 5 frozen browser goldens from 0f56e824...

diff -u /tmp/prototype-golden-attempt2-first.sha256 \
  /tmp/prototype-golden-attempt2-second.sha256
exit 0; 五项 SHA-256 完全一致

cmp docs/Mountain/webui-prototype-baseline/WEB-PARITY-004-manifest.json \
  /tmp/prototype-golden-attempt2-manifest-before.json
exit 0; manifest 原始字节完全一致
```

两次默认 capture 都只在临时目录截图并与已冻结 PNG/manifest 比较；不匹配会失败而不会覆写证据。
`--update` 是唯一写入基准的显式模式。脚本在本工作树的 loopback `127.0.0.1:5182` 启动 Vite preview，
Playwright Chromium 使用 `1366x900`、DPR 1；捕获页内冻结时钟并禁用 animation/transition，未改写原型源码。
脚本对 console error、pageerror、failed request 和 HTTP >=400 fail closed。两次运行均通过，且随后
`ss -ltn '( sport = :5182 )'` 无监听器；Owner worktree 仍干净。

## Golden 与可见证据

已抽查 manifest 与磁盘 PNG：五张均为 RGB `1366 x 900`，磁盘 SHA-256 与 manifest 一致。

| 组 | Route | Golden | SHA-256 |
| --- | --- | --- | --- |
| 品牌壳 | `/help` | `01-brand-shell.png` | `a33f02db0b429b3617a717279d926588cadd1c65debbe19c5c02a7c10836117a` |
| 任务队列 | `/projects` | `02-task-queue.png` | `2d6f574ec828a2742747a4c767572d0a089797b9c464f9e529905c7b344b47f5` |
| 六 Tab 新建任务映射 | `/create` | `03-create-six-tabs.png` | `993d4f8ee3d4490586c8f26e39d119366d67245a459e495d44a150a7c0bed545` |
| 设置 | `/settings` | `04-settings.png` | `c4049516bb0e945e02b2ff6c1f3cd128186a02bd83e6001e2ce94de23c36ac3f` |
| 资产 | `/assets` | `05-assets.png` | `0b42a9ab01306819137ae08343b04632b7b7b757db6e7dec592429488969b0c1` |

目视检查五张浏览器截图：分别显示品牌/帮助壳、任务队列、带六个 Tab 的新建任务页、设置页和资产管理页，
不是正式 WebUI actual 或裁切/拉伸图。manifest 固定 source commit
`0f56e824c0d49ab5c090e7ea07086dc9d47a9`，并明确历史 `/projects` 只映射正式 `/tasks` 视觉、`/create`
只映射正式 `/tasks/new` 视觉；未将旧 Project、mock 或 localStorage 契约迁入生产。

此 verdict 仅确认 PROTOTYPE-GOLDEN-005 交付满足其契约；不执行合并，也不自行解除或重新派发
`WEB-PARITY-004`。
