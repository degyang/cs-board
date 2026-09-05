# M09-INFRA-PLAN-003 — 统一 P3a bootstrap 职责边界

`worker_backend`（Codex medium），请只修复 `M09-INFRA-PLAN-002-V` 发现的 P3a 计划自相矛盾；不实施产品代码或 real render。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

输入：`docs/workmates/receipts/M09-INFRA-PLAN-002-V.md` 与更新后的执行计划。

输出：更新 `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md`，并写 `docs/workmates/receipts/M09-INFRA-PLAN-003.md`。

必须修正：

- P3a 必须明确、始终一致地检查并产出 Node、render script、锁定依赖、Remotion/browser、FFmpeg/ffprobe、服务/secret presence/probe 和 external-stage gate 的 bootstrap/toolchain 诊断；这些检查为只读、不可渲染、fail-closed，且不代表 `supported=true`。
- 删除或改写所有禁止 P3a 检查同一工具链条件的文字。仅禁止 P3a 执行真实 render、创建任务、读取/依赖 P6 evidence、activation 或开放提交。
- 同步架构段、P3a 输入/输出/test/entry/exit/禁止项、P4 合流、P6 entry、reason-code matrix、依赖图与 next queue，使同一 bootstrap contract 成为唯一真源。
- 明确 P3a 可独立验证的证据：每个工具/服务/gate 的检查、稳定 reason codes、多缺项优先级、bootstrap_ready 与 `supported=false` 并存的断言；P3b 仍是唯一 evidence activation。

禁止：改产品代码/测试、运行 real render、创建任务、打开 WebUI submission、改预置音色或提交推送。

出口：`READY_FOR_INDEPENDENT_PLAN_VERIFICATION`；回执给出消除矛盾的逐段定位。独立 PASS 前，P1 不得派发。
