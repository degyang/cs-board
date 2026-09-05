# PRESET-VOICE-UX-001-V — 预置音色独立验证

`tester_frontend`（Codex medium），在 `PRESET-VOICE-UX-001-FE` 与 `PRESET-VOICE-UX-001-BE` 回执均完成后，独立验证本项。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

输入：两个子工单、两个实现回执、相关 diff，以及 `PRESET-VOICE-UX-001.md`。

回执写入：`docs/workmates/receipts/PRESET-VOICE-UX-001-V.md`

独立验证：

- Provider 下拉只从 enabled 模型服务能力过滤而来，无厂商硬编码；预置卡片可新增、选择、编辑、保存。
- 试听只在独立页面底部试听区；默认文本和自定义文本正确，选中绑定正确 profile。
- 真实 preview API 的 profile/text 参数、加载、可播放成功、错误处理、切换后旧音频失效均经独立测试/检查；不得把 mock 成功或旧 URL 当真实 Provider 成功。
- 后端稳定复合身份与去重覆盖 MiMo 重复、同名异身份、total 一致、重建稳定性、adapter 参数和安全失败。
- 运行 focused frontend/backend tests、`cd web-v2 && npm test`、`cd web-v2 && npm run build`，以及受影响后端 suite；记录命令、退出码、数量、耗时。仅在确有必要时读取既有 5182/8000 状态，不重启服务。

不得修改实现、门禁或规划；不得执行动态信息图 real render；不得加 skip、提交或推送。出口必须为 PASS / FAIL / BLOCKED，并精确定位问题。
