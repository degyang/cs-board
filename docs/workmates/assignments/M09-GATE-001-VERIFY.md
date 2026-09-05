# M09-GATE-001-V — 独立门禁验证

`tester_backend`，请独立验证 M09-GATE-001。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

输入：`docs/workmates/assignments/M09-GATE-001.md`、worker 回执、相关 diff。

回执写入：`docs/workmates/agent-receipts/m09-gate-001-verifier.md`

必须验证：

- 检查 worker 改动未越过 assignment 的文件边界。
- 实际运行 worker 声称通过的 affected tests；检查无新增 skip、无删断言。
- 独立运行一次 `python -m pytest -q`，记录退出码、pass/fail/skip、耗时。
- 检查新 M09 代码不导入 `webapp.server`。

不得：修改实现、降低门禁、只引用 worker 结论、提交。

出口：PASS / FAIL / BLOCKED；必须附命令、退出码、数量、耗时和失败定位，并更新 `docs/workmates/board.md` 为 `acceptance` 或退回 `working`。
