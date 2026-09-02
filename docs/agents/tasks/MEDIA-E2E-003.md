# MEDIA-E2E-003：六阶段 Skills 手动执行闭环

- Owner: MEDIA
- Status: BACKLOG
- Priority: P1
- Depends on: `CORE-WO-003=APPROVED`, `WEB-WO-003=APPROVED`
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

依赖未批准前不得派发。派发前 PM 还必须确认用户输入、IndexTTS 健康和图片手动触发窗口。
