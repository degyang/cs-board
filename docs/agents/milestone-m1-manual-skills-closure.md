# M1：人工 Codex Skills 视频闭环

Status: `IN_PROGRESS`

## 唯一阶段目标

1. 用户能在正式 WebUI 新建 Task，提交视频文案与必要输入，并从真实 `/api/v1` 回读同一 Task；
2. 六个子工序的入口条件、出口条件、持久化输入、预期输出和人工 gate 在 WebUI/Work Order 中清晰可见、
   可由 task_id/run_id 安全读取；
3. 本阶段不实现或要求 auto/selective 编排。Codex 只根据 task_id/run_id 和持久化 Task，按项目 Skills
   人工逐阶段执行；
4. `generate-illustrations` 必须实际调用 Codex image generation 能力并经过人工候选 gate；禁止用脚本、
   mock、PIL、OpenAI-compatible provider 或其他图片服务冒充；
5. 六阶段完成后生成可播放 MP4，并保留每阶段输入、输出、hash、状态、人工 gate 与脱敏运行证据；
6. 上述工程门禁完成后，队列进入 `USER_ACCEPTANCE`：停止新增开发和自动派工，等待用户从正式 WebUI
   创建真实 Task 进行验收。只有用户能确认验收通过，PM/Worker/Reviewer 均不得代替宣布。

## 当前派工顺序

- 并行前置：`WEB-PARITY-004`、`CORE-RUNTIME-006`、`MEDIA-PREFLIGHT-004`；
- WEB 串行：`WEB-PARITY-004=APPROVED` 后派发 `WEB-WO-003`，同 Owner WIP=1；
- 最终闭环：`WEB-WO-003=APPROVED`、`MEDIA-PREFLIGHT-004=APPROVED` 且 live media readiness 全绿后，
  派发 `MEDIA-E2E-003`；
- 独立评审只由 Worker 的 `REVIEW_READY` 事件产生；任一 Changes Requested 沿原任务有界返工；
- `CEO-RECOVERY-002` 只负责不阻塞的调度恢复，不得变成产品长任务。

## 当前任务与目标的关系

- `WEB-PARITY-004`：把用户确认的 5182 golden 落到正式 WebUI，保证 Task 输入面可用；
- `CORE-RUNTIME-006`：证明真实 Mountain API/CLI 冷启动、错误边界、全量测试和清理可靠，避免人工链在
  运行前被后端挂起或脏进程阻断；
- `MEDIA-PREFLIGHT-004`：在不生产内容时验证真实媒体工具、服务、模型、临时工件、项目 Skills 与
  Codex imagegen 人工 gate 可用；
- `WEB-WO-003`：只读呈现每阶段持久化输入/预期输出/入口出口和人工下一动作，不实现编排；
- `MEDIA-E2E-003`：由 Codex 按 Skills 人工逐阶段完成真实 Task，图片阶段必须使用 Codex imagegen，
  最终形成可播放视频和完整证据。

## 阶段退出条件

- 上述五项交付均有独立 Reviewer 结论与 PM 状态决策；
- 正式 WebUI、真实 API、人工 Work Order/Skills 和最终 MP4 的证据形成完整 task_id/run_id 链；
- Dashboard 无遗留 working/blocked 假心跳，所有测试/服务/浏览器/媒体子进程已清理；
- `docs/agents/status.md` 改为 `USER_ACCEPTANCE`，关闭自动新任务生成/派工，仅保留用户验收响应入口。

任何未来 auto/selective、性能优化或非 M1 体验增强只能记为 `POST-M1`，本阶段不得派发。

