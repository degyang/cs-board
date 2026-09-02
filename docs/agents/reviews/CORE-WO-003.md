# CORE-WO-003 Review

- Reviewer: PM (`/root/pm`)
- Delivery: `a38ae67`（code `3836002`）
- Base: `e1bc3d5`
- Verdict: **CHANGES_REQUESTED**
- Next attempt: 2

## 已通过部分

- 变更局限于 Work Order 后端骨架、schema、API/CLI 和行为测试；没有进入 WebUI、Skills、candidate
  副作用或媒体执行；
- `StageWorkOrder`、当前文件与 revision envelope 持久化、fingerprint/ID 稳定性、安全 request 摘要、
  API/CLI 同源入口和相对路径基础校验已经形成；
- 独立定向门禁复现 `21 passed`，`git diff --check` 通过。

## P0：ready 与可执行性语义失真

在一个只有已保存 inputs、没有任何上游 Artifact 的真实新 Run 上复现：`clone-voice`、
`plan-storyboard`、`generate-illustrations`、`render-visuals`、`compose-video` 均返回：

```json
{
  "status": "ready",
  "input_artifacts": [],
  "commands": {"run": []},
  "next_action": {"code": "CAPABILITY_NOT_AVAILABLE"}
}
```

批准契约定义 `ready=输入完整`。当前实现只收集存在的输入，从不拒绝缺失输入；同时所有 Stage 共用
空 commands 和 unavailable next_action，即使其真实 Stage executor 已存在。Skills 无法据此区分
“可运行”“前置未完成”“等待人工触发”和“外部 Gate 未实现”。现有测试把所有六 Stage 无输入时
ready 写成预期，未覆盖工作条件。

## P0：插画受控目录不是自身 Work Order ID

实测 `work_order_id=wo-ee2d...`，但 `output_directory` 为
`manual/illustrations/candidates/wo-9f8a...`。契约要求
`manual/illustrations/candidates/<work_order_id>/<visual_id>`；两套 hash 会使 Codex 回存位置无法与
接受/审计对象稳定关联。

## P1：Schema 约束不足

当前 20 行 schema 只要求若干顶层字段；identity、commands item/argv、相对路径和未知字段缺少
类型/shape/path 约束。领域对象虽做了部分校验，但“schema-valid”门禁本身不能拦截多类非法 WO。

## 独立证据

```text
pytest -q tests/test_stage_work_orders.py tests/test_mountain_contracts.py tests/test_cli_csboard.py
21 passed, 2 warnings

新 Run 行为探针：五个有上游依赖的 Stage 均输出 status=ready、inputs=[]、run_commands=[]；
generate-illustrations 的 work_order_id 与 output_directory 尾 ID 不同。
```

## 有界纠偏

保留已有骨架，只修正缺失依赖、Stage-specific next action/run command、插画 ID/path、schema 和对应
行为测试。candidate import/validate/accept/reject/retry、WebUI、Skills 与 repository 架构重构均不在
attempt 2 范围。

## Attempt 2 review

Delivery `d6a73c0` 已通过上一轮四项复现和定向 `23 passed`，但仍为
**CHANGES_REQUESTED**，需 final attempt 3：

- `STAGE_OUTPUTS` 是单字符串映射，`clone-voice.expected_outputs` 漏掉 `timing.timeline`，
  `compose-video.expected_outputs` 漏掉 `output.final-video`，不符合六阶段规范主输出；
- current WO 因依赖消失被保存为 stale 后，相同 Artifact 恢复会命中“fingerprint 相同直接返回”分支，
  永久返回 stale，且未来副作用会复用旧 work_order/idempotency identity。

Attempt 3 只补输出集合、stale 恢复 revision/identity 与行为测试；不重开已通过项，不混入
capabilities API。
