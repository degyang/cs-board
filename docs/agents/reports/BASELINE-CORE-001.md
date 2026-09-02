# BASELINE-CORE-001 Review

- Worker baseline: `feat/mountain-assets-settings-backend@a5d5938`
- Verdict: `APPROVED`（审计结论通过，不代表被审计实现完成）

已确认 ExecutionPlan 的六阶段顺序、auto/selective 校验、输入原子持久化和既有 pipeline/telemetry 基础；专项相关测试为 97 passed。

关键缺口：

1. `selective` 只能保存，`start_run()` 固定返回 `EXECUTION_PLAN_NOT_READY`，pipeline run/resume 不读取 plan；
2. `GET inputs` 因 Task 序列化丢扩展字段，不能保真返回 `script_preparation` 和 `visual_anchor_enabled`；
3. Task 状态与 Run 不同步，Run 终态缺 `finished_at`；
4. 两个 CLI stage 分支仍调用已不存在的 provider helper；
5. 新产品只允许依赖 `/api/v1`，旧 `/api/mountain` 不进入冻结契约。

以上事实决定 CORE 下一轮优先级高于工作台扩展。
