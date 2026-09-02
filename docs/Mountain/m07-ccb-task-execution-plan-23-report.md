# CCB-TASK-EXECUTION-PLAN-23 Actual Delivery Report

## Scope and commit

本轮仅修改 `csboard`、`webapp` 后端契约/路由、CLI 可见性及后端测试；未修改 `web-v2`，未实现 selective pause/resume 或新的工作单格式。

## Delivered

- 新增 `ExecutionPlan` 不可变领域值对象。仅允许 `auto/selective`；校验空值、未知、重复和 legacy stage，并按六阶段 canonical 顺序规范化。`auto` 要求空列表，`selective` 至少一项。
- `POST /api/v1/tasks/{task_id}/inputs` 接收 `execution_mode` 与 JSON 字符串 `manual_stages`，非法 JSON/非数组/领域违规统一返回 400 `VALIDATION_ERROR`。
- execution plan 与 request、script preparation、reference 在既有 `commit_inputs` task lock/回滚事务中一起提交；无旁路文件。
- `GET /api/v1/tasks/{task_id}/inputs` 和 CLI `task show --task ... --json` 返回相同规范化 `execution_plan`；旧/缺失 manifest 默认 `{"mode":"auto","manual_stages":[]}` 且不重写。
- `start_run` 读取已保存计划；`selective` 返回 409 `EXECUTION_PLAN_NOT_READY`、`retryable=false` 和 suggestion，未创建/修改 Run、Stage、Event。
- 内部 `pipeline_run(policy=auto/gated/targeted)` 保持不变，与产品 execution plan 分层。

## Evidence

- `pytest -q tests/test_task_execution_plan_23.py`: **3 passed**。
- `python -m compileall csboard webapp cli scripts`: passed。
- `git diff --check`: passed。
- 手工 API smoke：selective 输入 readback 为 canonical 顺序；start 返回 409，run.json 字节哈希前后一致。

## Questions / Contract Gaps

- 全量 pytest 门禁在既有 `tests/test_mountain_server.py::test_inputs_and_start_boundary` 进入真实 pipeline 后超过 180 秒，命令以 timeout 124 结束；未观察到由本切片新增的断言失败。
- 禁止模式扫描仍命中 integration 基线已有的 legacy `/api/mountain/.../segment-script`（`webapp/mountain_api.py`、`webapp/mountain_stages.py`）。本轮未删除该 legacy API，以免扩大范围；它不属于新 Mountain Server 路由，但使 4S.5 的仓库级 grep 门禁无法通过，需 PM 决定后续清理切片。

## Gate summary

专项测试、compileall、diff-check 通过；全量 pytest 与仓库级 legacy grep 按上述 Contract Gaps 阻塞。工作树在提交前仅包含本报告及实现变更，未推送。
