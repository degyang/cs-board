# WEB-WO-003：任务工作台执行决策与 Work Order 只读面

- Owner: WORKER_WEB
- Status: PM_DECISION
- Priority: P1
- Depends on: `CORE-WO-003=APPROVED`
- Worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-webui-surface-parity`
- Branch: `feat/mountain-webui-surface-parity`
- Base commit: `9db741f`

## Goal

在新任务工作台准确展示 auto/selective 执行策略、manual gate、六阶段状态与 Work Order 下一动作，
让用户从 Task Queue 进入同一 run 控制每道工序，并看到输入指令与预期输出的安全只读引用。

## Acceptance boundary

- 严格消费后端 DTO，不在前端推断状态、fingerprint、路径或 provider 可用性；
- 只显示相对路径和安全摘要，不显示 Secret、完整 prompt/脚本或绝对路径；
- 有 API contract、组件交互和浏览器证据；原型表面对齐另按权威基准核验；
- 不添加 mock 业务数据，不修改后端，不自行设计外部 import/accept 语义。

`CORE-WO-003` 已批准，代码依赖满足。WEB 当前仍被 `WEB-INTAKE-003 → CORE-CAP-004` 占用，
不得重叠派发；待 intake 关闭后由 PM 固定 API commit/DTO、页面范围、截图场景与门禁。

## Recovery record

- `2026-09-02T18:30:00+08:00` — `recover-stale(runtime_idle)` re-dispatch authorized while
  status remains `DISPATCHED`; no Worker handoff or report exists. After this tracked record is
  committed and pushed, invoke only the restored supervised dispatcher asynchronously. Do not
  create an orchestrator Worker or write Worker runtime state.
- `2026-09-02T18:30:00+08:00` — `recover-stale` received for a missing `WORKER_WEB`
  runtime while this task remained `DISPATCHED`. No Worker delivery/report exists. The required
  `dispatch_cli_agent.sh` supervised dispatcher is unavailable from this checkout and the command
  path, so no compliant asynchronous recovery can be invoked. Blocked pending restoration of that
  dispatcher; do not create an orchestrator Worker or write a runtime record manually.
