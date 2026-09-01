#### CCB-TASK-INPUT-CONCURRENCY-14 测试证据报告 — 2026-09-01T09:55:43+08:00

- worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend`
- branch: `feat/mountain-assets-settings-backend`
- test commit: `6d40b27454ffb4c38be56152822e37bc799cc8c1 test(mountain): close same-task concurrency evidence`
- scope: 仅修改 `tests/test_input_transaction_11.py` 的两个同一 Task 并发测试；未修改生产代码。
- b_started: 两个测试均在线程 B 紧邻真实 `POST /api/v1/tasks/{task_id}/inputs` 前设置 `b_started`；主线程先断言 `b_started.wait(timeout=15)`，再断言 A 尚未释放时 `b_entered.is_set()` 为 false。
- b_entered: 两个测试在 A 释放、A/B 有界 join 后均断言 `b_entered.is_set()`，证明 B 后续经过同一生产 `request.after_install` checkpoint。
- A/B 响应: 两个测试均在线程内捕获 A/B 状态码或 `BaseException`；线程结束后先断言无异常，再明确断言 A=200、B=200。
- task/script_preparation 一致性: reference 并发测试读取最终 `task.json`，断言最终 `request.script` 精确等于 B 文案；按 `voice_units` 顺序拼接 text 后与该文案完全一致，并逐段断言 `source_range.start` 连续、text 等于对应切片、最终 end 覆盖全文。
- 保留证据: reference 测试继续断言最终相对路径 `inputs/reference.wav`、A 文件 sha256、staging 与 task 目录垃圾文件清零；不同 Task 并行测试未改动。

#### 门禁原始摘要

```text
$ env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q tests/test_input_transaction_11.py
......................                                                   [100%]
22 passed in 3.87s

$ env -u CSBOARD_ALLOW_PLAINTEXT_SECRETS /mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q
控制台原始回传：
..................................................................... [ 14%]
........................................................................ [ 30%]
执行宿主在进程完成后未回传尾部、退出码或汇总；本报告不将全量门禁表述为通过。

$ /mnt/d/workstation/projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts
Listing 'csboard' ...
Listing 'webapp' ...
Listing 'cli' ...
Listing 'scripts' ...
exit 0

$ ! rg -n "def _install_target|installed_request|old_request_bak|time\\.sleep" tests/test_input_transaction_11.py
exit 0（无匹配）

$ git diff --check
exit 0

$ git status --short
测试提交后为空；报告提交前仅本报告文件待提交。
```

- 未完成事项: 需在可保留全量 pytest 尾部与退出码的执行环境复核全量门禁；本次不修改生产代码，也不自行宣布审核通过。
