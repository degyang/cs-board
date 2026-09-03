# CCB-TASK-EXECUTION-PLAN-23 Final Correction Evidence

## Commits

- `test(mountain): complete execution plan behavior proof`（实现与测试提交见本地 commit）
- 本报告随后以 `docs(mountain): report final execution plan evidence` 提交

## Evidence

- ExecutionPlan/API、旧数据默认、selective 无副作用专项与服务回归：**25 passed in 2.68s**（组合门禁）。
- `test_inputs_and_start_boundary`：**1 passed in 1.67s**；根因是默认服务目录把缺少 required Secret 的 OpenAI 服务视为可用，导致真实 pipeline 外部调用；修复为 start_run 边界检查 required Secret，未修改 selective 编排。
- compileall、限定禁止模式扫描、diff-check 通过。
- 全量 pytest：当前工作树在 180 秒内仍于隐藏/环境注入的 `test_backend_runtime_17.py::test_smoke_checker_failure_path` 后无输出，以 timeout 124 结束；该源码不在当前 checkout，无法安全修改或删除断言。已记录为未通过门禁，不宣称验收通过。

## Contract coverage

事务使用既有 request/task/reference checkpoint 与锁；ExecutionPlan 同 request 原子提交。旧 request/未保存 inputs 读取默认 auto 且不改文件。跨 Task/run 先走 NotFound；selective start 对 Task 目录状态树不写入。CLI/API 使用同一 Application DTO。ServiceResolver 回归保留 required/optional Secret 选择语义，start_run 仅在能力边界阻断缺失 required Secret。

## Status

未修改 `web-v2`，未实现 Stage Work Order/selective 编排；工作树在本地提交后保持 clean。全量门禁挂起仍待 PM 处理环境注入测试根因。
