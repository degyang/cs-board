# WEB-PM-001 — WebUI 阶段调度与验收

`pm`，请负责 WebUI 阶段的非阻塞调度与最终验收。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

遵照：`docs/workmates/team-contract.md`、`docs/workmates/board.md`。

回执写入：`docs/workmates/receipts/WEB-PM-001.md`

本轮动作：

- 只消费 `WEB-LOCAL-002`、`WEB-ENV-001` 和随后 `WEB-LOCAL-002-V` 的回执。
- 未有 worker 回执时保持可响应，不实施代码、不运行长测试。
- tester PASS 后核对 5182 可见结果，记录 ACCEPTED 或 CHANGES_REQUIRED。
- ACCEPTED 后把动态信息图规划任务置为 ready，但不得自行开放提交入口。

注意事项：不得把执行者自测当作独立验收，不得提交或推送。
