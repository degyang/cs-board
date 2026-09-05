# PRESET-VOICE-UX-001 — 预置音色体验与真实试听

目标：完善预置音色的卡片式管理与独立试听，同时保证 Provider 从模型服务能力动态导出、真实 preview 链路可用、MiMo 目录无重复。

子工单：

- `PRESET-VOICE-UX-001-FE`：前端交互、页面布局和前端测试
- `PRESET-VOICE-UX-001-BE`：voice-profiles 目录身份/去重与真实 preview API 契约
- `PRESET-VOICE-UX-001-V`：两项完成后独立验证

共同边界：不修改 `docs/Mountain/` 的动态信息图规划；非必要不重启 5182/8000；不提交、不推送。动态信息图 submission 继续关闭。
