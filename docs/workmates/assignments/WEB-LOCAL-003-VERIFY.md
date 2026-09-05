# WEB-LOCAL-003-V — Whisper 排除修复独立复验

`tester_frontend`，请复验 `WEB-LOCAL-003`。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

输入：`docs/workmates/receipts/WEB-LOCAL-002-V.md`、`docs/workmates/assignments/WEB-LOCAL-003.md`、`docs/workmates/receipts/WEB-LOCAL-003.md`、最新 `WEB-ENV-001` 回执。

回执写入：`docs/workmates/receipts/WEB-LOCAL-003-V.md`

必须验证：真实形状 `local-whisper + adapter_type=whisper + capability=speech_alignment` 被排除；正常 alignment 服务仍显示；focused test、完整 `npm test`、build 均正常退出；5182 served module 包含当前结构化过滤且只有一个监听进程。

不得：修改实现、降低门禁、添加 skip、只引用 worker 结论。

出口：PASS / FAIL / BLOCKED，附退出码、数量、耗时和现场 PID。
