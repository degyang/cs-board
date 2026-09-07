# NEXT-FE-001 — 预置音色前端收口

状态：working。Owner：frontend（Codex `gpt-5.6-terra / medium`）。

## Goal

在 `/mnt/d/Workstation/Projects/cs-board-worktrees/frontend`、分支 `workmates/frontend`、基线 `e34ba6e83ef1a6c3ec3ad5274485505379ce0a21` 上，核对并收口预置音色页面，使其达到可交给 CC 独立视觉/行为验收的冻结状态。

权威输入：集成区 `docs/workmates/team-setup.md`、`docs/workmates/receipts/PRESET-VOICE-UX-004-FE.md`、`docs/workmates/receipts/PRESET-VOICE-UX-003-V.md`，以及 `docs/Mountain/29-voice-provider-and-infographic-plan.md` 的音色要求。旧 worker worktree 的 board 不是当前状态。

## Scope / Ownership

- 只写 `frontend/**` 和本 worktree 的 `docs/workmates/receipts/NEXT-FE-001.md`。
- 先运行 `npm --prefix frontend ci` 准备独立依赖；不得链接或复用别的 worktree 的可写 `node_modules`。
- 核对当前提交是否已包含：1024/1440 双栏、列表滚动且试听区可见、vendor+remote voice 去重、PATCH DTO、无 provider model 时可见终态、试听超时和旧音频失效。
- 若实现已有且门禁通过，不制造改动；若有可复现缺口，做最小修复并补有意义的回归。
- 可在 5184 启动前端用于视觉证据，但当前 proxy 指向集成 8000；服务未健康时先完成不依赖服务的工作并在回执说明。
- 不改 Python/API、共享看板、配置源、动态信息图；不创建/编辑真实用户音色数据。

## Done Predicate

- 专项音色测试、前端全量测试、`npm --prefix frontend run build` 均 exit 0，无 skip。
- 若后端健康，使用真实浏览器核对 1024×900 与 1440×900 的完整页面和右侧创建/编辑位置；不提交写请求。截图保存在 `/tmp/next-fe-001-*`，回执列出路径和页面来源。
- `git diff --check` 通过；有实现改动则创建一个本地提交，无改动则记录目标 HEAD。不得 merge/push。
- 写回执，包含实际命令、计数、commit、diff、未验证项及 CC 精确复验入口。完成后停止，等待 PM。
