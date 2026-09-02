# CS Board Agent Coordination

近期目标：用户通过新 WebUI 创建 Task，系统形成六阶段可执行工作单，Codex 按 Skills 完成阶段并生成可播放视频。

| Task | Owner | Status | Contract | Delivery | Review |
| --- | --- | --- | --- | --- | --- |
| `BASELINE-WEB-001` | WEB | APPROVED | `docs/agents/tasks/BASELINE-WEB-001.md` | `docs/agents/reports/BASELINE-WEB-001.md` | PM accepted |
| `BASELINE-CORE-001` | CORE | APPROVED | `docs/agents/tasks/BASELINE-CORE-001.md` | `docs/agents/reports/BASELINE-CORE-001.md` | PM accepted |
| `BASELINE-MEDIA-001` | MEDIA | APPROVED | `docs/agents/tasks/BASELINE-MEDIA-001.md` | `docs/agents/reports/BASELINE-MEDIA-001.md` | PM accepted |
| `CORE-EXEC-002` | CORE | REVIEW_READY | `docs/agents/tasks/CORE-EXEC-002.md` | `ea7b54f` | PM review pending |
| `MEDIA-WO-002` | MEDIA | REVIEW_READY | `docs/agents/tasks/MEDIA-WO-002.md` | `7bc8af9` | PM review pending |

首轮只读审计已完成。下一轮由 CORE 修复执行计划与输入回读的 P0 契约；WEB 完成分支集成前保持空闲，MEDIA 只冻结 Work Order/外部产物边界，不抢先实现依赖 CORE 的运行状态。
