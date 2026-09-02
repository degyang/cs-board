# CORE-WO-003：Stage Work Order v1 后端骨架

- Owner: CORE
- Status: BACKLOG
- Priority: P0
- Depends on: `CORE-EXEC-002=APPROVED`, `MEDIA-WO-002=APPROVED`
- Worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend`
- Branch: `feat/mountain-assets-settings-backend`
- Base commit: dispatch 时由 PM 固定

## Goal

按已批准 `stage-work-order-v1.md` 落地 WO 领域 DTO、持久化、状态读取和只读 API/CLI 骨架，使六阶段
都能从 persisted Task/Run/ExecutionPlan 生成确定性工作单，但不实现外部插画成果提交事务。

## Acceptance boundary

- 六阶段 envelope、相对路径校验、fingerprint、revision 与状态机具备真实持久化和行为测试；
- Application 是唯一状态写入者，API/CLI 不复制决策；
- `work-order show` 可被 Skills 消费，响应不含 Secret、Provider URL、绝对路径或完整文案；
- 不修改 WebUI，不执行付费/本地媒体生成，不实现 candidate accept，不合并分支。

依赖未全部批准前不得派发。派发时 PM 必须补齐精确 base、允许文件、测试命令和报告路径。
