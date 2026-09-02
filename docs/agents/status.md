# CS Board Agent Coordination

近期目标：用户通过新 WebUI 创建 Task，系统形成六阶段可执行工作单，Codex 按 Skills 完成阶段并生成可播放视频。

| Task | Owner | Status | Contract | Delivery | Review |
| --- | --- | --- | --- | --- | --- |
| `BASELINE-WEB-001` | WEB | APPROVED | `docs/agents/tasks/BASELINE-WEB-001.md` | `docs/agents/reports/BASELINE-WEB-001.md` | PM accepted |
| `BASELINE-CORE-001` | CORE | APPROVED | `docs/agents/tasks/BASELINE-CORE-001.md` | `docs/agents/reports/BASELINE-CORE-001.md` | PM accepted |
| `BASELINE-MEDIA-001` | MEDIA | APPROVED | `docs/agents/tasks/BASELINE-MEDIA-001.md` | `docs/agents/reports/BASELINE-MEDIA-001.md` | PM accepted |
| `CORE-EXEC-002` | CORE | APPROVED | `docs/agents/tasks/CORE-EXEC-002.md` | `e1bc3d5` | `docs/agents/reviews/CORE-EXEC-002.md` |
| `MEDIA-WO-002` | MEDIA | APPROVED | `docs/agents/tasks/MEDIA-WO-002.md` | `7bc8af9` | `docs/agents/reviews/MEDIA-WO-002.md` |
| `PM-AUTO-001` | PM | APPROVED | `docs/agents/tasks/PM-AUTO-001.md` | `fa840d7` | `docs/agents/reviews/PM-AUTO-001.md` |
| `CORE-WO-003` | CORE | IN_PROGRESS | `docs/agents/tasks/CORE-WO-003.md` | pending | worker active |
| `WEB-INTAKE-003` | WEB | IN_PROGRESS | `docs/agents/tasks/WEB-INTAKE-003.md` | pending | worker active |
| `MEDIA-SKILLS-003` | MEDIA | DISPATCHED | `docs/agents/tasks/MEDIA-SKILLS-003.md` | pending | waiting only for one runtime agent slot |
| `WEB-WO-003` | WEB | BACKLOG | `docs/agents/tasks/WEB-WO-003.md` | pending | blocked by CORE-WO-003 |
| `MEDIA-E2E-003` | MEDIA | BACKLOG | `docs/agents/tasks/MEDIA-E2E-003.md` | pending | blocked by CORE-WO-003 + WEB-WO-003 |

## 当前决策

- `CORE-EXEC-002` attempt 2 已批准；`CORE-WO-003` 的两个依赖均满足并已派发。
- `MEDIA-WO-002` 契约已批准但未合并；CORE 通过固定 commit/path 只读消费该契约，不改写其产品语义。
- WEB 与 MEDIA 各增加一个不依赖 Work Order 生产 DTO 的真实并行切片；它们不改变原三个 BACKLOG 的依赖关系。
- 当前 orchestrator 只有四个活跃槽位（含 `/root` 和 `/root/pm`）；CORE、WEB 已启动，MEDIA 已派发并将在 PM 释放槽位后立即唤醒。这是运行时容量，不是代码依赖。
- PM 协调线程为 `/root/pm`。Worker 完成后必须按注册表直接唤醒 PM，而不是只通知 `/root` 或等待用户追问。

## 队列规则

1. 优先级按任务契约中的 `Priority`，同优先级按依赖拓扑排序；
2. `BACKLOG` 只有在全部 `Depends on` 均为 `APPROVED` 后才能由 PM 改成 `READY`；
3. Worker 同一时间只领取一项 `DISPATCHED` 任务；返工沿用原任务并递增 attempt；
4. PM 审核写入 Git 后，必须在同一轮计算并派发下一个满足依赖的 `READY` 任务；
5. Dashboard 心跳只表示有限租约内的真实活动，不表示 Agent 能跨会话自行运行。
