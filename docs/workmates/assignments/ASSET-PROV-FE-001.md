# ASSET-PROV-FE-001 — 任务资产预览与生成配置交互骨架

状态：done （ASSET-PROV-V-001 独立验证 PASS）
Owner：frontend
工作区：`/mnt/d/Workstation/Projects/cs-board-worktrees/frontend`

## Goal

在现有任务队列/任务详情中建立可测试的资产卡片交互骨架：图片预览、音频试听、视频播放，以及支持鼠标、键盘、触屏的“生成配置”入口和编辑抽屉。当前阶段不调用尚未冻结的再生成 API。

## Authority

1. 集成区 `docs/Mountain/30-artifact-provenance-and-regeneration.md`
2. 集成区 `docs/workmates/assignments/ASSET-PROV-001.md` 中的字段边界
3. `AGENTS.md`

## Ownership

- 可写：现有前端任务详情/队列的直接相关组件、样式、类型、测试及 `docs/workmates/receipts/ASSET-PROV-FE-001.md`。
- 不可写：后端、schema、API client 的真实再生成调用、服务配置、真实任务数据、看板。
- 你不是代码库中唯一执行者；不得回滚他人改动。工作树仍使用旧目录名时只在该工作树内工作，回执注明集成时映射到主区 `frontend/`。

## Required behavior

- 同一资产卡片支持 image/audio/video 三种预览行为。
- 点击资产主体打开或执行预览；配置入口默认克制隐藏，但 hover、focus-within 和触屏可达。
- 配置抽屉展示实际传入的 generation record JSON 字段，不由 UI 猜测；允许编辑提示词和明确允许的参数。
- “再次生成”在本切片必须呈禁用/未接线状态并说明等待后端契约，不能伪造成功或写 localStorage。
- 不显示 Secret、Authorization 或项目外绝对路径字段。

## Done predicate

- 覆盖三类预览、鼠标/键盘/触屏入口、抽屉编辑、敏感字段隐藏、未接线再生成状态的直接测试。
- focused tests、完整 frontend tests、build 全部 0 failed、0 skipped。
- 回执含文件清单、测试数量/耗时、截图或可复核 DOM 证据、未接 API 边界。
- 不提交、不推送；完成后停止等待 PM 和独立验证。
