# CCB-TASK-EXECUTION-PLAN-23 纠偏报告

## Commits

- 实现：待提交 `fix(mountain): prove task execution plan invariants`
- 本报告：待提交 `docs(mountain): report execution plan correction evidence`

## 纠偏结果

- canonical 六阶段现由 `csboard.domain.execution_plan.CANONICAL_STAGES` 单一提供；Pipeline 通过该领域常量生成 `STAGE_ORDER`。
- `manual_stages` 仅 `None` 默认空数组；空字符串、非数组、非字符串元素等均进入 `VALIDATION_ERROR`。
- `start_run` 先读取并校验 Task/Run 归属，再检查 execution plan；selective 返回 409，不写 Task/Run/Stage/Event/Audit/Logs/Artifacts。
- ServiceResolver 不再把缺少必需 Secret 的服务视为可运行，修复边界测试进入真实外部 pipeline 的挂起根因。

## 门禁证据

- 挂起定位命令：`test_inputs_and_start_boundary` **1 passed in 1.67s**。
- 专项：`tests/test_task_execution_plan_23.py` **3 passed**。
- compileall、限定禁止模式扫描、`git diff --check` 通过。
- 全量 pytest 在当前环境于 `tests/test_backend_runtime_17.py::test_smoke_checker_failure_path` 后持续无输出，45 秒定位命令未完成；需 PM 复核该环境/测试收集来源。未使用 skip、放宽 timeout 或删除断言。

## Contract Gaps

本轮未修改 `web-v2`、未实现 selective 编排或 Stage Work Order。全量门禁仍需解决 runtime smoke failure 测试挂起后才能声明通过。
