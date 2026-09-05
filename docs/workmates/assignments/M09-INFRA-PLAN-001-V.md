# M09-INFRA-PLAN-001-V — 动态信息图规划独立验证

`tester_backend`（Codex terra medium），请对 `M09-INFRA-PLAN-001` 进行独立、只读验证。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

输入：

- `docs/workmates/assignments/M09-INFRA-PLAN-001.md`
- `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md`
- `docs/workmates/receipts/M09-INFRA-PLAN-001.md`
- 两份既有 29 计划和被规划文档引用的当前代码/测试路径

回执写入：`docs/workmates/receipts/M09-INFRA-PLAN-001-V.md`

只读边界：

- 可读取文档、代码、测试、Git 状态和 diff，以核验陈述是否有证据；不得修改产品代码、测试、配置、服务、既有计划或规划文档。
- 不执行 real render、不创建任务、不启动/重启服务、不开放或实现动态信息图 WebUI submission；不得以任何 mock/fake 结果宣称 real-render 成功。
- 除本验证回执外不得写入文件；不提交、不推送、不加 skip、不删除断言。

必须独立核验以下七项并逐项给出 PASS / FAIL / BLOCKED、引用位置和依据：

1. 规划是否把两份既有 29 计划与当前代码、测试及未提交差异逐项区分为已具备、缺失、冲突或待澄清，且没有把草案当作已实现。
2. 是否定义了边界清晰、依赖方向正确的目标架构，覆盖 domain、storyboard adapter、Remotion renderer adapter、capability、Task/API/CLI、输出/恢复以及错误和 secret 脱敏责任。
3. 是否给出有序依赖图和可独立验收的工作包；每包是否都有目标、允许边界、输入/输出、测试、entry/exit gate、验收证据和禁止项。
4. 是否把真实渲染前置条件、real smoke evidence、capability fail-closed 语义和 fake/real E2E 分层明确为门禁，而没有偷换成已经执行的 real render。
5. 是否明确 legacy 识别、只读隔离、迁移决策点，以及阻止新 `infographic-remotion` 回落旧 renderer/旧路径的测试策略。
6. 是否规定 outputs task-package 的位置、命名/元数据、状态/错误、恢复、证据和清理/保留规则，并明确不开放 WebUI submission。
7. 是否给出最小、可分派的 next queue，含严格依赖、执行顺序和每张票的独立验证角色，且未把规划完成误作实现授权。

还须核验：规划回执声称的只读范围与文档事实一致；规划本身未引入产品代码或 real-render 执行痕迹。不得只复述实现者结论。

出口：

- `PASS`：七项及附加只读边界都被独立证实；规划可以交由 PM 决定是否接受，但仍不授权实现。
- `FAIL`：具体列出缺失项、矛盾或无证据陈述，且不修改规划。
- `BLOCKED`：只在无法读取必要输入时使用，说明精确缺失路径。

回执必须包含检查的文件/命令（如有）、退出码（如有）、结论和精确失败定位。
