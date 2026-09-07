# ASSET-PROV-BE-003 — 任务内当前关键资产发现 API

状态：working
Owner：backend
工作区：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`

## Goal

在已通过独立验证的 generation-record store 与单资产 GET API 之上，提供任务/运行内当前关键资产的可发现列表，让前端无需猜测 asset ID、类型、生成记录或媒体 URL。

## Authority

1. `docs/Mountain/30-artifact-provenance-and-regeneration.md`
2. `docs/workmates/assignments/ASSET-PROV-BE-002.md`
3. `docs/workmates/receipts/ASSET-PROV-BE-002-V.md`
4. `AGENTS.md`

## Ownership

- 可写：已有 generation-record store、Task API 与直接测试，及 `docs/workmates/receipts/ASSET-PROV-BE-003.md`。
- 不可写：前端、Provider/再生成、媒体替换、下游失效、真实数据、共享看板。
- 保留所有既有差异；不回滚、不提交、不推送。

## Required behavior

- 新增 `GET /api/v1/tasks/{task_id}/runs/{run_id}/assets`，仅枚举该 run 下 `assets/<asset-id>/generation.json` 的 current records。
- 每项返回稳定 `asset_id`、`asset_kind`、完整实际 `generation_record` 和服务端给出的相对 `media_url`；前端不应自行拼路径。
- 列表顺序必须稳定；忽略不是资产目录的项，但不得静默吞掉存在却 schema/身份/路径无效的 `generation.json`。
- task/run 不存在、路由越界或记录无效使用结构化错误，响应不泄露绝对路径、Secret 或文件系统内部。
- 保持 BE-002 两个单资产 URL 与错误合约不变；不写当前 8000 或真实 `outputs/`。

## Done predicate

- store 与 API 测试覆盖 image/audio/video 三项列表、稳定顺序、完整原记录、正确相对 media URL 和空列表。
- 反向覆盖记录损坏、identity 不符、task/run 缺失、路由越界和无绝对路径泄露。
- 独立可复跑的 TestClient/ASGI HTTP 测试必须覆盖新列表 URL；不能只调 route function。
- 运行 generation-record 直接测试与受影响后端门禁，0 failed、0 skipped，并记录命令、退出码、数量、耗时。
- 回执说明返回形状、diff、测试和仍未实现的再生成/替换/失效边界；完成后停止等待独立验证。
