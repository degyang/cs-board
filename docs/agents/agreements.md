# CEO 工作约定时间线

本文件是用户与团队工作约定的追加式历史。新约定只能追加；被替代的节点保留并改标
`SUPERSEDED`，不得删除。CEO 在每个有事件的调度周期先读取最新 `ACTIVE` 节点，再处理任务队列。

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
