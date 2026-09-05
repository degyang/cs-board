# M09-INFRA-PLAN-002 回执

状态：仅文档计划修正完成；未实施产品代码、未修改测试/配置、未创建任务、未执行 real render、未开放动态信息图提交。

读取依据：`docs/workmates/receipts/M09-INFRA-PLAN-001-V.md` 与 `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md`。

已修正：

- 将原 P3 拆为 **P3a bootstrap readiness** 和 **P3b evidence activation**。P3a 只读、可解释、fail-closed 地检查工具链/服务/配置/浏览器/FFmpeg readiness；不执行 render，不读 P6 evidence，且 Node、`node_modules` 或 mock 绝不能使公开 capability 为 available。
- P3b 只在 P6 成功并已有独立复核的真实任务包 evidence 后才可 activation；`create-options`/capability 只有当前 P3a readiness、完整且已复核、hash/probe/manifest 一致且新鲜的 evidence 全部成立时，才返回 `infographic-remotion available/supported=true`。
- P6 entry 已改为 P1、P2、P3a、P4、P5 的独立 exit 加当前 `bootstrap_ready=true`；P6 只生成真实 MP4、ffprobe、hash/manifest/freshness evidence，不自行 activation。P3b 依赖 P6，没有任何回边。
- 依赖图与队列统一为 DAG：P1 PASS 后 P2 与 P3a 并行；二者 PASS 后 P4 → P5 → P6 → P3b → create-options/task-submission 联调。P4 明确在 activation 仍 unavailable 时只能保留受控 internal/test 通道，不得开放用户/API/WebUI 提交。
- 补充 fail-closed reason codes（含 `BOOTSTRAP_NOT_READY`、`REAL_SMOKE_EVIDENCE_REQUIRED`、`EVIDENCE_INVALID`、`EVIDENCE_EXPIRED`、`EVIDENCE_NOT_INDEPENDENTLY_VERIFIED`）及 24 小时 freshness、hash/tool/browser/service/gate 变更即失效规则。
- 保留 P1–P5、legacy separation、任务包规则、真实 MP4+ffprobe 证据以及禁止 WebUI submission 的原有边界；§7 每票都列出实现者、独立验证者、entry/exit 条件，可自动派发的首票为 P1。

未解决风险：真实工具链、浏览器来源、外部 stage services 和图像 gate 尚无 P6 real-render evidence；因此现阶段必须保持 `available/supported=false`，不得开启用户提交。

完成出口：`READY_FOR_INDEPENDENT_PLAN_VERIFICATION`。未实施产品代码、未修改测试/配置、未创建任务、未执行 real render、未开放动态信息图提交，也未自行接受计划。
