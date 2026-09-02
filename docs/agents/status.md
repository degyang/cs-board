# CS Board Agent Coordination

近期目标：用户通过新 WebUI 创建 Task，系统形成六阶段可执行工作单，Codex 按 Skills 完成阶段并生成可播放视频。

| Task | Owner | Status | Contract | Delivery | Review |
| --- | --- | --- | --- | --- | --- |
| `BASELINE-WEB-001` | WEB | APPROVED | `docs/agents/tasks/BASELINE-WEB-001.md` | `docs/agents/reports/BASELINE-WEB-001.md` | PM accepted |
| `BASELINE-CORE-001` | CORE | APPROVED | `docs/agents/tasks/BASELINE-CORE-001.md` | `docs/agents/reports/BASELINE-CORE-001.md` | PM accepted |
| `BASELINE-MEDIA-001` | MEDIA | APPROVED | `docs/agents/tasks/BASELINE-MEDIA-001.md` | `docs/agents/reports/BASELINE-MEDIA-001.md` | PM accepted |
| `CORE-EXEC-002` | CORE | CHANGES_REQUESTED | `docs/agents/tasks/CORE-EXEC-002.md` | `ea7b54f` | `docs/agents/reviews/CORE-EXEC-002.md` |
| `MEDIA-WO-002` | MEDIA | APPROVED | `docs/agents/tasks/MEDIA-WO-002.md` | `7bc8af9` | `docs/agents/reviews/MEDIA-WO-002.md` |
| `PM-AUTO-001` | PM | APPROVED | `docs/agents/tasks/PM-AUTO-001.md` | `fa840d7` | `docs/agents/reviews/PM-AUTO-001.md` |
| `CORE-WO-003` | CORE | BACKLOG | `docs/agents/tasks/CORE-WO-003.md` | pending | blocked by CORE-EXEC-002 + MEDIA-WO-002 |
| `WEB-WO-003` | WEB | BACKLOG | `docs/agents/tasks/WEB-WO-003.md` | pending | blocked by CORE-WO-003 |
| `MEDIA-E2E-003` | MEDIA | BACKLOG | `docs/agents/tasks/MEDIA-E2E-003.md` | pending | blocked by CORE-WO-003 + WEB-WO-003 |

## 当前决策

- `CORE-EXEC-002` 进入 attempt 2，仅纠正 CLI 仍索取旧参数、构造无效 adapter 的问题；既有执行计划实现与已通过测试必须保留。
- `MEDIA-WO-002` 契约已批准，但不合并；后续 CORE 实现任务仍需等待 `CORE-EXEC-002` 批准。
- PM 已提前建立三项依赖队列。依赖未满足的任务保持 `BACKLOG`，不得派发或改成 `READY`。
- PM 协调线程为 `/root/pm`。Worker 完成后必须按注册表直接唤醒 PM，而不是只通知 `/root` 或等待用户追问。

## 队列规则

1. 优先级按任务契约中的 `Priority`，同优先级按依赖拓扑排序；
2. `BACKLOG` 只有在全部 `Depends on` 均为 `APPROVED` 后才能由 PM 改成 `READY`；
3. Worker 同一时间只领取一项 `DISPATCHED` 任务；返工沿用原任务并递增 attempt；
4. PM 审核写入 Git 后，必须在同一轮计算并派发下一个满足依赖的 `READY` 任务；
5. Dashboard 心跳只表示有限租约内的真实活动，不表示 Agent 能跨会话自行运行。
