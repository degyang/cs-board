# M09-INFRA-PLAN-001 — 动态信息图实施规划收敛

`worker_backend`（Codex medium），请只完成动态信息图的实施规划，不实施任何产品代码。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

依据：

- `docs/Mountain/29-voice-provider-and-infographic-plan.md` §§5–6
- `docs/Mountain/29-m09-infographic-work-breakdown.md`
- 当前工作树、相关 domain/application/adapters/CLI/API 代码与现有测试

输出：

- 规划文档：`docs/Mountain/29-m09-dynamic-infographic-execution-plan.md`
- 回执：`docs/workmates/receipts/M09-INFRA-PLAN-001.md`

必须完成：

1. 逐项对照两份既有 29 计划与当前代码/测试/未提交 diff，列出已具备、缺失、冲突或需要澄清的事实；不要把计划中的设想当成已实现。
2. 定义目标架构与边界：领域模型、storyboard 适配器、Remotion renderer 适配器、capability、任务创建/API/CLI 接线、任务输出与恢复链路；明确依赖方向和错误/secret 脱敏责任。
3. 给出有序、可独立验收的工作包和依赖图。每个包必须写明：目的、允许修改的文件/模块边界、输入/输出契约、测试、entry gate、exit gate、验收证据和禁止项。
4. 明确 real-render 前置条件和门禁：本机 Node/Remotion 工具链、已验证的真实渲染最小产物、可用性/probe 语义、失败时不得伪造成功，以及 fake 与 real E2E 的分层。
5. 明确 legacy separation：旧渲染/旧任务路径的识别方式、隔离/禁止复用规则、迁移或兼容决策点，以及如何用测试防止新 `infographic-remotion` 回落到旧路径。
6. 制定 outputs task-package rules：每个任务包的产物位置、命名/元数据、状态/错误表达、可恢复性、验证证据及清理/保留原则；不得把动态信息图提交入口或 WebUI 提交流程纳入本阶段。
7. 以可执行的 next queue 收尾：列出最小下一批可分派工单、严格依赖关系、推荐执行顺序和每张票的独立验证角色。规划本身的完成不得自动授权实现。

限制：

- 只可新增/修改上述规划文档与本回执；不修改产品代码、测试、配置、服务进程或现有 29 计划。
- 不运行会改变环境的 real render，不创建任务，不开放或实现动态信息图 WebUI submission。
- 不提交、不推送；不删除断言、不加 skip。

完成门槛：规划可由 PM 按上述七项逐项审阅，且 next queue 中的每个实现包都有明确的独立验证出口；回执列出实际检查过的代码/文档范围及尚存风险。
