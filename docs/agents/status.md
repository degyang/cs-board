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
| `CORE-WO-003` | CORE | APPROVED | `docs/agents/tasks/CORE-WO-003.md` | `1c5e9ce` | `docs/agents/reviews/CORE-WO-003.md` |
| `WEB-INTAKE-003` | WEB | IN_PROGRESS | `docs/agents/tasks/WEB-INTAKE-003.md` | `0b99b50` | independent WEB unit active with backend `6699d20` |
| `MEDIA-SKILLS-003` | MEDIA | APPROVED | `docs/agents/tasks/MEDIA-SKILLS-003.md` | `6fc2924` | `docs/agents/reviews/MEDIA-SKILLS-003.md` |
| `CORE-CAP-004` | CORE | APPROVED | `docs/agents/tasks/CORE-CAP-004.md` | `c567c3a` | `docs/agents/reviews/CORE-CAP-004.md` |
| `CEO-RECOVERY-002` | PM | IN_PROGRESS | `docs/agents/tasks/CEO-RECOVERY-002.md` | pending | real CLI CEO registered; implementation active |
| `CORE-CAP-005` | CORE | APPROVED | `docs/agents/tasks/CORE-CAP-005.md` | `7ac3cb0` | `docs/agents/reviews/CORE-CAP-005.md` |
| `WEB-WO-003` | WEB | READY | `docs/agents/tasks/WEB-WO-003.md` | pending | dependency approved; waits for WEB-INTAKE-003 |
| `MEDIA-E2E-003` | MEDIA | BACKLOG | `docs/agents/tasks/MEDIA-E2E-003.md` | pending | blocked by CORE-WO-003 + WEB-WO-003 |
| `DASH-STATS-003` | DASH | DISPATCHED | `docs/agents/tasks/DASH-STATS-003.md` | pending | dispatched to `/root/dashboard_stats` |

## 当前决策

- `CORE-EXEC-002` attempt 2 已批准；`CORE-WO-003` 的两个依赖均满足并已派发。
- `MEDIA-WO-002` 契约已批准但未合并；CORE 通过固定 commit/path 只读消费该契约，不改写其产品语义。
- WEB 与 MEDIA 各增加一个不依赖 Work Order 生产 DTO 的真实并行切片；它们不改变原三个 BACKLOG 的依赖关系。
- WEB intake 自动化已真实发现 native Mountain Server 缺少 `/api/v1/capabilities`；前端保持阻塞，后端修复已进入 READY，不允许 WEB 吞掉 404。
- MEDIA Skills 主体方向正确，但首阶段 Artifact 映射和未实现 illustration retry 说明矛盾，进入有界 attempt 2。
- CEO/PM 协调线程为注册表中的真实 Codex CLI UUID。Worker 完成后必须按注册表直接唤醒 CEO，
  而不是只通知 `/root` 或等待用户追问。
- `CORE-CAP-004` attempt 2 已补齐真实依赖图并获批准；同一 `WEB-INTAKE-003` 已恢复，先完成 intake
  浏览器证据，再领取 `WEB-WO-003`。
- 当前 orchestrator 会话树已失效，`CEO-RECOVERY-002` 负责注册真实 CLI CEO、修复 stale work 检测，
  并恢复 `WEB-INTAKE-003`；恢复完成前不得把 `WEB-WO-003` 并发派给同一 WEB Owner。
- CEO 首次恢复周期核验 WEB 推送提交 `0b99b50` 后，确认并非遗失执行，而是新的 CORE 集成缺口：
  capabilities 调用了消费基线不存在的 public registry method。WEB 转为 `BLOCKED`，`CORE-CAP-005`
  使用固定 WEB base 做最小自包含修复；其独立审核通过前不得恢复 WEB。
- `CORE-CAP-005` 的独立审核已通过，CEO 批准交付 `7ac3cb0`；WEB 已注册为真实 Codex CLI 会话并恢复
  `WEB-INTAKE-003`，只引入自包含实现 `6699d20` 后重跑原 intake 门禁。`WEB-WO-003` 继续等待，不得并发。

## 队列规则

1. 优先级按任务契约中的 `Priority`，同优先级按依赖拓扑排序；
2. `BACKLOG` 只有在全部 `Depends on` 均为 `APPROVED` 后才能由 PM 改成 `READY`；
3. Worker 同一时间只领取一项 `DISPATCHED` 任务；返工沿用原任务并递增 attempt；
4. PM 审核写入 Git 后，必须在同一轮计算并派发下一个满足依赖的 `READY` 任务；
5. Dashboard 心跳只表示有限租约内的真实活动，不表示 Agent 能跨会话自行运行。
