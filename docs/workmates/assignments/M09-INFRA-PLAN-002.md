# M09-INFRA-PLAN-002 — 消除 P3/P6 循环并收敛激活门禁

`worker_backend`（Codex medium），请只修订动态信息图执行计划，不实施产品代码、测试或 real render。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

输入：`docs/Mountain/29-m09-dynamic-infographic-execution-plan.md`、两份既有 29 计划，以及 `M09-INFRA-PLAN-001` 产物。

输出：

- 更新 `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md`
- 回执 `docs/workmates/receipts/M09-INFRA-PLAN-002.md`

必须完成：

1. 消除 P3 对 P6 evidence、同时 P6 又依赖 P3 的循环。将 P3 明确拆为：
   - **P3a bootstrap readiness**：只读、可解释、fail-closed 的工具链/服务/配置/浏览器/FFmpeg readiness；不执行 render，也不能据 Node/node_modules 或 mock evidence 宣称 available。
   - **P3b evidence activation**：仅在 P6 成功并独立复核的真实任务包 evidence（真实 MP4、ffprobe、hash/manifest、freshness）存在时，才使 create-options / capability 对 `infographic-remotion` 公开真实 `available/supported=true`。
2. 重写 P3、P6、依赖图、real-render 门禁和 next queue，使依赖为有向无环图；明确 P6 依赖 P1/P2/P4/P5 与 P3a，而 P3b 依赖 P6。说明 P4 如何在 capability 仍 unavailable 时保留受控 internal/test 的真实任务通道而不开放用户提交。
3. 定义 `create-options` 的真实 available 条件、稳定 reason codes、evidence freshness/invalidating rules，并明确 P6 失败或 evidence 缺失/过期时返回 unavailable，禁止伪造可用。
4. 保持既有 P1–P5、legacy separation、task-package rules、真实 MP4+ffprobe 证据与“不得开放 WebUI submission”的边界一致；如改动任一工作包依赖/出口，逐项交叉引用。
5. next queue 必须可自动派发：PLAN-002 PASS 后首张实现票为 P1；P1 独立 PASS 后才派 P2 与 P3a（可并行）；随后 P4→P5→P6→P3b→create-options/task-submission 联调。列出每票实现者、独立验证者、entry/exit gate。

禁止：改产品代码、运行 real render、创建任务、打开动态信息图 WebUI submission、改前端预置音色相关文件、提交或推送。

完成出口：`READY_FOR_INDEPENDENT_PLAN_VERIFICATION`；回执逐项说明循环如何被解除、哪些文本/图/队列被更新，以及未解决风险。不得自行接受计划。
