# ASSET-PROV-001 — 关键资产生成记录 Schema 与领域契约

状态：done （ASSET-PROV-V-001 独立验证 PASS）
Owner：backend
工作区：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`
集成基线：主工作区目录迁移尚未提交；本任务不得改动 `webapp/`、`web-v2/` 或旧运行目录名称。

## Goal

为图片、音频、视频建立统一、可验证且不泄露 Secret 的生成记录契约，作为后续单资产预览、编辑参数、局部再生成和原子替换的唯一结构基础。

## Authority

1. `docs/Mountain/30-artifact-provenance-and-regeneration.md`
2. `docs/Mountain/03-artifact-contracts.md`
3. `AGENTS.md`

## Ownership

- 可写：`schemas/artifacts/` 下新增的 generation record schema、直接 schema 测试、`docs/workmates/receipts/ASSET-PROV-001.md`。
- 不可写：前后端服务目录、现有任务仓储、UI、看板、配置/真实素材、其他 worker 文件。
- 你不是代码库中唯一执行者；保留并适应他人改动，不回滚、覆盖或清理不属于本任务的差异。

## Required contract

- 覆盖稳定 `asset_id`、asset kind、task/run/stage/unit/visual identity、revision、parent revision、attempt ID/status、输入资产引用、提示词、允许公开的 Provider/模型参数、随机种子、项目相对输出路径、MIME、sha256、时间与错误摘要。
- 图片、音频、视频使用同一基础结构，通过明确的 kind-specific 参数分支表达差异；不能复制三套漂移 schema。
- 路径必须是 `outputs/<task-id>/...` 范围内的项目相对路径，拒绝绝对路径与 `..`。
- schema 必须拒绝常见 secret/header 字段；不得把真实 Secret 写入 fixture。
- 当前记录与 attempts 历史的边界必须可表达；成功替换使用 revision，失败尝试不能冒充 current。

## Done predicate

- 新 schema 可被项目现有 Draft 2020-12 验证入口加载。
- 正向 fixture 至少覆盖 image/audio/video；反向测试覆盖绝对路径、路径穿越、Secret 字段、缺失 revision、失败 attempt 冒充 current。
- 运行直接 schema 测试与相关 artifact-contract 测试，0 failed、0 skipped。
- 回执记录文件清单、关键决定、命令、退出码、数量、耗时和仍未实现的 API/UI 边界。
- 不提交、不推送；完成后停止，等待 PM 消费 diff 与独立验证。
