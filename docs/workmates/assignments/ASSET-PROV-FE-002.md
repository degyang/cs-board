# ASSET-PROV-FE-002 — 任务工作台接入当前资产发现 API

状态：working（2026-09-06 PM reconciliation revision）
Owner：frontend
工作区：`/mnt/d/Workstation/Projects/cs-board-worktrees/frontend`

## Goal

在已独立接受的 `ArtifactPreviewCard` 骨架上，接入已接受的 `GET /api/v1/tasks/{task_id}/runs/{run_id}/assets`，让任务工作台直接消费服务端返回的稳定 asset identity、完整 generation record 与 media URL，展示 image/audio/video 当前资产；不得猜测 asset ID、类型或路径。

## Authority

1. `docs/Mountain/30-artifact-provenance-and-regeneration.md`
2. `docs/workmates/receipts/ASSET-PROV-V-001.md`
3. `docs/workmates/receipts/ASSET-PROV-BE-003-V.md`
4. `AGENTS.md`

## PM reconciliation decision

This assignment was drafted and partially started by the supervisor before an
active PM authorized it. The PM **revises and adopts** it now: preserve every
existing frontend diff in place, but do not treat it as completed or create a
receipt until all revised predicates below are met. The accepted BE-003 and
BE-003-V receipts remain the immutable backend contract; no backend change is
authorized.

The preserved partial implementation already has typed list DTOs, an API
request, and initial states. Review rather than discard it. A live PM review
found that the initial render placed the new asset section inside the old
artifact-table non-empty branch. Correct that: a non-empty current-assets
response must be visible even if the legacy artifact list is empty.

## Ownership

- 可写：`web-v2/` 中任务工作台、API client/types、直接样式与测试，以及 frontend worktree `docs/workmates/receipts/ASSET-PROV-FE-002.md`。
- 不可写：后端、schema、Provider、再生成执行、二进制替换、下游失效、共享看板。
- 保留所有既有差异；不回滚、不提交、不推送。

## Required behavior

- 从当前任务可用的 run identity 请求 `/api/v1/tasks/{task_id}/runs/{run_id}/assets`；若当前页面尚无稳定 run identity，明确展示不可用/空态，不从旧 artifact 路径反推。
- 当前资产区必须独立于旧 artifact 表是否为空：旧表为空且新列表有数据时，三类当前资产仍须显示；旧表保留原有空态。
- 使用后端 item 原样传递 `asset_id`、`asset_kind`、`generation_record`、`media_url` 给预览卡；支持 image/audio/video，并保持配置入口的鼠标、键盘、触屏可达性。
- loading、空列表、404/400/网络失败必须有清晰且不泄露内部路径的 UI 状态；请求竞态或任务/run 切换不能把旧响应显示到新任务。
- media URL 只通过既有 API base 解析机制消费，不能手拼 `outputs/` 或绝对文件路径。
- “再次生成”继续 disabled，并保持“等待后端再生成契约”的真实边界；不得新增伪成功、本地替换或未存在的 POST。

## Done predicate

- 使用 MSW/现有 HTTP mock 层覆盖三类资产、稳定服务端顺序/identity、legacy artifact 空而 current-assets 非空、loading、空列表、结构化 4xx、网络失败和任务/run 切换竞态；断言请求的是实际列表 URL，旧响应不得覆盖新 task/run。
- 回归既有卡片 hover/focus/touch、敏感字段过滤和三类媒体预览。
- 聚焦测试、frontend 全量测试、TypeScript/Vite build、`git diff --check` 全部干净退出，记录命令、退出码、数量、耗时、warnings/skips。
- 回执说明返回形状、实际接线、状态 UI、diff 与仍未实现的再生成/替换/失效边界；完成后停止等待独立验证。
