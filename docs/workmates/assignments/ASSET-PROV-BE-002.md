# ASSET-PROV-BE-002 — 关键资产生成记录持久化与只读 API

状态：done （ASSET-PROV-BE-002-V 独立验证 PASS）
Owner：backend
工作区：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`

## Goal

在已通过独立验证的 generation-record schema 上建立真实的任务内持久化、语义校验和只读 API，使前端后续可以按 `asset_id` 获取当前 revision 的真实 JSON 与安全媒体地址。本票不实现“再次生成”。

## Authority

1. `docs/Mountain/30-artifact-provenance-and-regeneration.md`
2. `docs/workmates/assignments/ASSET-PROV-001.md` 及已验证 schema
3. 现有 `FilesystemTaskRepository` / artifact API 的路径和错误合约
4. `AGENTS.md`

## Ownership

- 可写：generation-record 领域/端口/文件系统实现、直接后端 API 路由、直接测试及 `docs/workmates/receipts/ASSET-PROV-BE-002.md`。
- 不可写：前端、Provider 调用、任务或单元重跑、原子替换当前二进制、下游失效策略、服务/音色配置、真实素材、共享看板。
- 保留并隔离 `NEXT-BE-001` 的既有未提交差异；不回滚或改写他人工作。

## Required behavior

- 按任务边界保存 `outputs/<task-id>/runs/<run-id>/assets/<asset-id>/generation.json` 与 `attempts/<attempt-id>.json`；禁止绝对路径、`..` 和 task/run/asset 身份交叉写入。
- 写入前先做 Draft 2020-12 schema 校验和跨字段语义校验：路径 task ID 必须与 identity 一致，路由 task/run/asset 必须与记录一致。
- 持久化采用同目录临时文件加原子替换；校验失败时不得产生半写 JSON。
- 只读 API 至少支持按 task/run/asset 获取 current generation record 和媒体内容/安全 URL；缺失、身份不符、schema 无效、路径越界使用现有结构化错误合约，不泄露绝对路径。
- API 返回的 JSON 是实际 `generation.json`，不重新拼装；Secret/header/credential 字段依然必须被 schema 拒绝。
- 不更改当前 8000 集成进程的数据，不写真实 `outputs/`。

## Done predicate

- 直接测试覆盖 image/audio/video 三种 current 记录的保存与读取，以及 attempt 历史。
- 反向覆盖路径越界、task/run/asset 身份不符、schema 无效、Secret 字段、缺失记录，并证明原 current JSON 不被失败写入破坏。
- API 合约测试证明返回持久化原文与可读媒体，错误不含项目外绝对路径。
- 运行直接测试与受影响后端门禁，0 failed、0 skipped；记录命令、退出码、数量和耗时。
- 回执列出 diff、结构决策、未实现的 regeneration/替换/失效边界。不提交、不推送；完成后停止并等待独立验证。
