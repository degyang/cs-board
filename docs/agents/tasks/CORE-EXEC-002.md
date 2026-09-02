# CORE-EXEC-002：执行计划成为运行决策源

- Owner: CORE
- Status: READY
- Worktree: `/mnt/d/Workstation/Projects/cs-board/.claude/worktrees/mountain-foundation-backend`
- Branch: `feat/mountain-assets-settings-backend`
- Base commit: `a5d5938`

## Goal

让已保存的 `ExecutionPlan` 成为 Application、`/api/v1` 和 CLI 的唯一执行策略来源，并修复 inputs 写入后回读不保真的 P0 缺陷。

## Required behavior

1. `auto` 继续按六阶段规范顺序运行；
2. `selective` 的 `manual_stages` 表示这些阶段必须由 stage run/retry 显式触发，其他阶段由 pipeline 连续执行；
3. pipeline 到达尚未执行的 manual stage 时必须无副作用暂停，并返回结构化执行决策，至少包含 `state=waiting-manual-trigger`、`next_stage`、`manual_stages`；
4. 手动阶段成功后，resume 从同一 run 继续，直到下一人工门禁或终态；
5. targeted stage 仍补齐缺失/stale 前置依赖，但不能绕过前置人工门禁；
6. start、pipeline run/resume、stage run/retry 和 CLI 读取同一 plan，不允许各自推断策略；
7. `GET /tasks/{task_id}/inputs` 必须保真返回已持久化的 `script_preparation`、`visual_anchor_enabled` 和 `execution_plan`；写入→重载 repository→API/CLI readback 必须相等。

执行决策应与 Stage 业务状态分离；本任务不得只添加前端字符串，也不得把 `waiting-manual-trigger` 伪装成 Stage `failed`。如必须扩展公共 DTO，先在报告的 Contract Decision 中写明字段、状态和兼容性。

## Non-goals

- 不实现 Stage Work Order、外部插画 import/accept 或媒体 E2E；
- 不修改 `web-v2`；
- 不修复旧 `/api/mountain`；
- 不更换 Provider、TTS、Whisper、Renderer 或 FFmpeg；
- Task 生命周期同步和 CLI provider helper 属于后续 P1，除非本任务测试证明是执行决策正确性的直接阻塞。

## Acceptance and gates

- auto/selective 矩阵覆盖：顺序、每个可能暂停点、多个 manual stages、失败、retry、resume、stale、targeted 前置；
- 暂停前后验证 provider/stage/Artifact 无意外副作用；
- Application、API、CLI subprocess 三入口观察到相同决策；
- inputs 对旧数据有确定性默认，对新数据完整 round trip；
- 并发 start/resume 不重复执行同一阶段；
- 错误和 telemetry 不泄露 reference 路径、Secret 或完整文案；
- 既有审计中的 97 个相关测试继续通过，并新增真实行为测试；
- 运行项目全量后端测试；如超时，必须定位具体测试，不能只报告 timeout。

## Delivery

在 `docs/agents/reports/CORE-EXEC-002.md` 写实际提交、DTO decision、测试命令和结果、已知缺口。提交并推送当前分支后通知 PM，停止，不进入 Work Order。
