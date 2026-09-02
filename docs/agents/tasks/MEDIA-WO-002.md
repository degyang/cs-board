# MEDIA-WO-002：Stage Work Order 与外部插画 Gate 契约冻结

- Owner: MEDIA
- Status: READY
- Worktree: `/mnt/d/workstation/projects/cs-board-media`
- Branch: `feat/mountain-media-work-orders`
- Base commit: task dispatch commit

## Goal

基于真实代码和 `docs/Mountain/24-codex-six-stage-execution-contract.md`，冻结可由 CORE 实现、WEB 展示、Codex Skills 消费的 Stage Work Order v1，以及 `generate-illustrations` 外部候选成果闭环。此轮是契约交付，不实现生产运行代码。

## Required contract

- 六阶段共用 envelope：identity、revision/fingerprint、status、input artifacts、parameters/instructions 相对路径、output directory、expected outputs、结构化 commands；
- 明确 task/run/stage/unit/visual 作用域和规范相对路径；
- 明确 `ready/waiting-manual-trigger/waiting-external-output/validating/waiting-acceptance/succeeded/failed/stale` 的所有者与迁移；
- commands 使用 argv/结构化对象，不保存 shell 字符串、Secret、Provider URL 或绝对路径；
- 插画 candidate source/processed 分层以及 import/validate/accept/reject/retry 的请求、响应、幂等键和错误码；
- validate 至少覆盖格式、尺寸、hash、visual coverage 与候选来源；
- accept 后才能提交正式 `illustrations.manifest` 并放行 render；
- 上游 revision 变化后 fingerprint 失效与局部 stale 传播；
- 给出一份完整 illustration Work Order JSON 和一次局部 Visual retry 示例；
- 列出 WEB 所需只读 DTO 与 Skills/CLI 消费约束。

## Non-goals

- 不修改 Python/TypeScript 生产代码和 schemas；
- 不运行付费图片、IndexTTS、Whisper、render 或 compose；
- 不决定 WebUI 视觉布局；
- 不引入动态信息图、桌面端或 Legacy 兼容。

## Acceptance and gates

- 文档中的每个路径、Artifact key 和现有六阶段名称均与当前代码/Schema 对照；
- JSON 示例可被标准 JSON parser 读取；
- 状态迁移无无法退出的中间态；
- 两次 import/accept/retry 的幂等语义明确；
- 用户只承担素材与效果判断，不承担路径、hash、manifest 或 CLI 拼装；
- CORE 和 WEB 可以仅凭文档分别实现后端和只读界面，不需要重新做产品决策。

## Delivery

新增 `docs/agents/contracts/stage-work-order-v1.md` 与示例 JSON，并在 `docs/agents/reports/MEDIA-WO-002.md` 记录核对结果。提交并推送当前分支后通知 PM，停止，不实现生产代码。
