# PM-AUTO-001：独立 PM、依赖队列与真实在线状态

- Owner: PM
- Status: REVIEW_READY
- Priority: P0
- Depends on: none
- Worktree: `/mnt/d/workstation/projects/cs-board-mountain-v2`
- Branch: `integration/mountain-v2`

## Goal

将 PM 从用户接口 `/root` 分离为 `/root/pm`，提前维护依赖队列，使用事件直接唤醒审核和派工，并让
Dashboard 只显示有限租约内的真实活动；为线程树失效提供无事件零模型调用的外部恢复入口。

## Acceptance

- 注册表、状态、任务和审核文档均由 Git 跟踪；
- 至少三项后续任务具有 Priority 与 Depends on，依赖未满足时不可派发；
- Worker 完成后直接唤醒 PM，PM 同轮审核并选择下一项；
- PM/Worker heartbeat 有界，到期显示 idle；
- 事件探针没有事件时不输出、不调用模型；重复事件在 ack 后不重复唤醒；
- 外部脚本没有真实 CLI UUID 时明确 not-configured，不伪称自治。

## Delivery

实现提交为 `fa840d7`，证据见 `docs/agents/reports/PM-AUTO-001.md`。该协调基础设施由 `/root`
审核；实现者 PM 不自批、不合并。
