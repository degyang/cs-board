# PRESET-VOICE-UX-002-V — 预置音色创建契约独立复验

`tester_frontend`（Codex medium），请独立复验 `PRESET-VOICE-UX-002-BE`，并确认它重新满足 `PRESET-VOICE-UX-001` 的验收门槛。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

输入：`PRESET-VOICE-UX-001*.md`、`PRESET-VOICE-UX-002-BE.md`、相应回执与 diff。

回执写入：`docs/workmates/receipts/PRESET-VOICE-UX-002-V.md`

必须独立验证：

- 使用真实 in-process API（非 mock）提交当前前端相同的预置音色 create body，刻意不含 `profile_id`；应成功并返回稳定、合法 ID。
- 重复 POST、重建读取、同名但不同 provider/model/remote-voice identity 的不碰撞，以及 MiMo 去重/total 规则。
- 检查前端没有为修复而引入厂商/ID 硬编码，Provider 仍仅由 enabled 音频/TTS能力服务导出；复跑已有预置音色的选中、独立试听、文本、preview、旧音频失效和错误态测试。
- 运行 focused 后端和前端测试、`cd web-v2 && npm test`、`cd web-v2 && npm run build`；记录命令、退出码、数量与耗时。

不得修改实现或规划、不得重启 5182/8000、不得执行 real render、不得提交/推送或加 skip。出口 PASS / FAIL / BLOCKED；只有 PASS 才可供 PM 接受。
