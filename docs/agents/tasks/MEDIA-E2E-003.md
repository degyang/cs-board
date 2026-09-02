# MEDIA-E2E-003：六阶段 Skills 手动执行闭环

- Owner: WORKER_MEDIA
- Status: BACKLOG
- Priority: P1
- Depends on: `CORE-WO-003=APPROVED`, `WEB-WO-003=APPROVED`, `MEDIA-PREFLIGHT-004=APPROVED`
- Worktree: dispatch 时由 PM 分配独立 worktree
- Branch: dispatch 时由 PM固定
- Base commit: dispatch 时由 PM 固定

## Goal

使用真实 Task 产生的六阶段 Work Order，通过项目 Skills 逐阶段执行、回存、校验和验收，最终生成
可播放 MP4，并形成 WebUI 后续自动/选择性调试所需的可重复 E2E 证据。

## Acceptance boundary

- 用户只提供文案、参考音频、风格选择与效果判断；路径、命令、manifest、hash 由系统生成；
- 插画必须采用手动 Codex `imagegen` 触发与候选验收边界，未验收不得继续渲染；
- IndexTTS、Whisper、render、compose 使用真实服务/工具并保留脱敏日志与 Artifact 证据；
- 不使用 placeholder/Fake/PIL 代替出图，不改产品范围，不自动产生付费外部调用。
- Codex 必须从持久化 Task/Run 读取每阶段输入与 Work Order，按项目 Skills 人工逐阶段执行；本任务不实现
  auto/selective 编排。`generate-illustrations` 阶段必须实际使用 Codex image generation 能力，禁止脚本、
  mock、PIL 或其他 provider 代替，并保留候选、hash、人工 gate 与正式 Artifact 的对应证据。

依赖未批准前不得派发。派发前 PM 还必须确认用户输入、MEDIA live readiness 全绿、IndexTTS 健康和
Codex imagegen 人工触发窗口。交付获独立审核后只进入 `USER_ACCEPTANCE`，不得继续自动生成开发任务。
