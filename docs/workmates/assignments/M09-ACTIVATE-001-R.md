# M09-ACTIVATE-001-R — activation review corrections

状态：assigned

Owner：`backend`（独立工作区 `/mnt/d/Workstation/Projects/cs-board-worktrees/backend`）；PM 负责审查与集成，`verification` 负责后续独立复验。

你不是代码库中的唯一执行者。保留已有 V1/V2 和资产来源改动，不回滚他人修改，不修改集成区看板，不提交、合并或推送。

## 输入与目标

先读 `AGENTS.md`、`docs/workmates/team-setup.md`、集成区 `docs/workmates/assignments/M09-ACTIVATE-001.md`，以及 backend worktree 的 `docs/workmates/receipts/M09-ACTIVATE-001.md` 与当前 diff。

PM 审查判定原回执尚不能进入独立验证，必须完成以下修正：

1. 恢复 `REAL_SMOKE_EVIDENCE_REQUIRED = "REAL_SMOKE_EVIDENCE_REQUIRED"` 的既有公开常量语义；激活 pointer 缺失仍可由新 verifier 投影为 `EVIDENCE_MISSING`，但不得通过改写旧常量让旧测试静默接受新语义。
2. 恢复 `tests/test_cli_capabilities.py` 对 `webapp.*` import 的原架构守卫。不得把它改成仅禁止 `backend.*`；如需同时禁止 backend，可新增断言，但不能移除 webapp 守卫。
3. 审核所有本任务改过的既有测试，恢复任何为了适配实现而改变的旧断言/旧覆盖；新增激活行为必须用新增测试或严格增强测试表达。
4. `tests/test_infographic_activation_projection.py` 当前只 mock `CapabilityService`，不能证明 API/CLI/任务创建消费真实同一投影。补充至少一个不 mock capability service 的隔离临时夹具，验证 capability snapshot、`create_options()` 与 create task 的正向一致；同时验证 pointer/receipt 或关键哈希失效后，三处同步关闭且 create task 以 `CAPABILITY_NOT_AVAILABLE` 拒绝。不得写规范 outputs，不得执行 renderer。
5. 复核回执里的最终 SHA-256；原回执列出的 `commands.py`、`cli/csboard.py`、`mountain_capability_api.py`、`mountain_server.py`、`test_infographic_activation.py` 哈希与现场文件不一致，必须在所有修正完成后重算并明确列出。

## 允许范围

沿用 `M09-ACTIVATE-001` 的允许实现/测试范围，仅可为以上修正修改 backend worktree 内的激活、capability、composition glue 与直接测试，以及本任务回执。不要启动 8000/5182，不创建 render/task/run，不改 frozen V3 产物，不改 frontend、assignment 或 board。

## 验证与回执

- 运行覆盖 activation、capability、create-options、task creation、API/CLI 的 focused tests；列出命令、exit code 和数量。
- 运行 scoped `git diff --check`。
- 原完整 serial backend gate 已通过；若本轮最终实现/测试变更影响相关路径，重新运行完整 serial gate。不得用共享数据目录的四分片 race 作为产品 PASS，也不得因此降低测试。
- 更新 backend worktree `docs/workmates/receipts/M09-ACTIVATE-001.md`，给出 `READY_FOR_VERIFY` 或 `CHANGES_REQUIRED`，记录修正前因、最终文件哈希、实际门禁及未验证范围。

停止条件：若无法同时恢复既有契约并保持激活正向路径成立，保持公开关闭，写 `CHANGES_REQUIRED` 后停止。
