# CEO 工作约定时间线

本文件是用户与团队工作约定的追加式历史。新约定只能追加；被替代的节点保留并改标
`SUPERSEDED`，不得删除。CEO 在每个有事件的调度周期先读取最新 `ACTIVE` 节点，再处理任务队列。

## TEAM-FLOW-20260902 — CEO、PM、Tester 与五泳道

- Time: `2026-09-02T18:30:00+08:00`
- Status: `ACTIVE`
- Source: `USER-DIRECTIVE`

### 约定内容

1. CEO 由 timer 短周期触发，只负责阶段目标、全局停滞、资源闲置与跨角色阻塞治理；不实现、不跑长门禁、不作任务验收。
2. PM 根据 CEO 目标拆分和派发任务；Tester 交付证据进入审核泳道后，PM 只核对证据与范围，写最终状态并判断是否生成后续任务。
3. `tester_web` 与 `tester_core` 为固定领域 Tester；`tester_media` 等其他领域 Tester 按任务动态注册，完成后按超时与容量策略回收。
4. Tester 只运行门禁并提交 PASS、FAIL 或 BLOCKED 证据，不修改实现、不批准任务、不创建或派发任务。
5. 唯一标准泳道为：待办 → 工作 → 验证 → 审核 → 已完成；不再设置独立 Reviewer 角色。
6. Worker、Tester、PM、CEO 状态必须来自真实受监督进程；进程失败必须显示 blocked，不得以 idle 掩盖。

### CEO 跟踪

- 定期检查工作、验证、审核泳道的等待时长以及待办与空闲资源是否同时存在。
- 审核泳道积压时唤醒 PM；验证泳道积压时分配匹配领域 Tester；工作阻塞时要求 PM 拆分诊断或调整资源。
- 正常 Worker→Tester→PM 接力由事件直接触发，CEO timer 只负责异常恢复，不介入正常流转。

## M1-MANUAL-SKILLS-20260902 — 第一阶段人工 Codex Skills 视频闭环

- Time: `2026-09-02T15:58:38+08:00`
- Status: `ACTIVE`
- Source: `54208e4`

### 约定内容

1. 正式 WebUI 必须允许用户新建 Task，并提交视频文案与必要输入。
2. 六个子工序必须明确展示入口条件、出口条件、持久化输入、预期输出与人工 Gate。
3. 第一阶段不实现 auto/selective 编排；后续由 Codex 根据 task_id/run_id 按项目 Skills 手工执行。
4. 插画生成必须真实使用 Codex image generation，并经过人工候选 Gate；不得用脚本、mock 或其他图片服务冒充。
5. 六阶段最终必须生成可播放 MP4，并保留完整、脱敏、可追溯的阶段证据。
6. 上述条件完成后进入 `USER_ACCEPTANCE`，停止新增开发与自动派工，由用户从 WebUI 创建真实任务验收。

### CEO 跟踪

- 每个有任务事件的调度周期先回顾本节点，再检查当前派工是否直接服务于第一阶段目标。
- WEB、CORE、MEDIA、DASH、PM 维护跨角色滚动队列，但 M1 期间不得派发无关的 POST-M1 工作。
- Worker 交付必须独立审核；PM、Worker、Reviewer 均不得代替用户宣布最终验收通过。
- 后续用户调整目标时追加新的时间线节点，保留本节点作为历史记忆。

## MODEL-ESCALATION-20260902 — Agent 能力渐进升级与用户审批

- Time: `2026-09-02T16:34:00+08:00`
- Status: `ACTIVE`
- Source: `USER-DIRECTIVE`

### 约定内容

1. 新任务默认使用与工作复杂度匹配的适中模型和 reasoning effort，不得因任务重要而直接分配最高能力。
2. 返工优先缩小问题边界并保持适中配置；同一任务连续三次返工仍未解决，CEO 才能提出能力升级申请。
3. 任何 Agent 使用 `gpt-5.6-sol` 且 reasoning effort 为 `high`、`xhigh`、`max` 或 `ultra` 前，必须取得用户针对该任务的明确审批。
4. 未获审批不得写入注册表、任务契约或启动命令；误启动的超线任务必须立即停止并改回最低充分配置。

### CEO 跟踪

- 每次创建角色、派工或调整模型前检查初始配置、返工次数和审批记录。
- 一次审批只适用于明确的角色、任务和等级，不自动覆盖后续任务。
- Dashboard 注册表必须反映实际运行配置，不保留已停止的高等级配置。

## TEAM-ELASTICITY-20260902 — 动态角色回收

- Time: `2026-09-02T16:42:00+08:00`
- Status: `ACTIVE`
- Source: `USER-DIRECTIVE`

### 约定内容

1. Agent 角色不是固定席位；已完成交付且没有 READY、DISPATCHED、IN_PROGRESS、REVIEW_READY 或 CHANGES_REQUESTED 任务时，应从当前团队注册表回收。
2. 回收只移除当前成员和瞬时运行态，历史任务、报告、审核与提交记录必须保留。
3. 后续出现对应职责的有界任务时，CEO 可按适中能力重新注册该角色。

### CEO 跟踪

- 每个调度周期检查无待办且长期 idle 的角色，避免面板制造虚假团队容量。
- `DASH-STATS-003` 已批准且无后续 DASH 任务，因此本周期回收 DASH；面板服务本身继续作为基础设施运行。
