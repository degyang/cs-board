# M09-INFRA-PLAN-003 回执

状态：**READY_FOR_INDEPENDENT_PLAN_VERIFICATION**。仅修改 `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md` 并更新本回执；未修改产品代码、测试或配置，未创建任务，未执行 real render，未开放任何提交入口。

依据：已读取 `docs/workmates/receipts/M09-INFRA-PLAN-002-V.md`，并仅修复其指出的 P3a bootstrap/toolchain 职责自相矛盾。

## 已消除的 P3a 矛盾（逐段定位）

- **§2 架构（Capability 段）**：P3a 现为唯一 bootstrap/toolchain 诊断真源，明确检查 Node、render script、锁定依赖、Remotion 实际使用的 browser、FFmpeg/ffprobe、服务/secret presence/probe 和 external-stage gate；其输出始终不等同 `supported=true`。
- **§3 P2 exit**：P2 只消费 P3a 所定义的 prerequisite contract，完成 adapter 契约和 fake 测试；不再拥有或探测独立的 renderer readiness，从而避免同一工具链条件双重归属。
- **§3 P3a 输入、输出、测试、entry/exit、禁止项**：删除“非 renderer”及禁止检查 toolchain 的冲突文字。P3a 现在逐项产出工具/服务/gate 诊断、`bootstrap_ready`、检查时间及安全 reason code；明确只读、fail-closed、不可 render/create/activation/读取 P6 evidence，并明确 `bootstrap_ready=true` 与 `supported=false` 并存的回归断言。
- **§3 P4 合流、依赖图和说明**：P4 合流 P3a 的唯一 bootstrap/toolchain 诊断与 P2 adapter 契约完成；P2 与 P3a 均只依赖 P1、可以并行，P3a 不读取 P2 adapter 产物，故没有反向边。
- **§3 P6 entry、P3b entry/input、§4 reason-code matrix**：P6 要求 P3a 当前 `bootstrap_ready=true` 但不依赖 P3b；P3b 读取 P6 独立复核证据、当前 P3a 和 P4 合流。§4 新增 P3a 稳定首缺项优先级，涵盖 Node/script/lockfile/Remotion/browser/FFmpeg/ffprobe/service-secret/service-probe/external-stage；P3b activation code 保持单独的 `READINESS_FAILED`/evidence 类错误，不能用 P3a 细节替代。
- **§7 next queue**：保持唯一 DAG `P1 → (P2 ∥ P3a) → P4 → P5 → P6 → P3b/P7`，且明确仅在 PLAN-003 **独立 PASS** 后才可派 P1；本回执不自行接受计划。

## 保留的边界与自检

- `create-options available/supported` 仍只由 P3b activation 决定：真实 MP4、ffprobe、artifact index/manifest/hash、新鲜 evidence、独立复核和当前 readiness 缺一不可。
- P3a 不执行真实 render、不创建任务、不读取/依赖 P6 evidence、不 activation 或开放提交；P3b 仍是唯一 evidence activation。
- P1–P5、legacy read-only separation、任务包规则、P6 real MP4+ffprobe 与 WebUI submission 禁令未改变。
- 静态复查使用 `rg` 检索 P3a/P2/P4/P6/P3b/next queue/reason-code 交叉引用，并运行 `git diff --check -- docs/Mountain/29-m09-dynamic-infographic-execution-plan.md`，结果通过；未运行测试，以遵守纯规划范围。

请求独立验证：请核对 P3a 是否在 §2、P3a 包、P4/P6/P3b、reason-code matrix、依赖图和 next queue 中均为同一个完整 bootstrap/toolchain contract；确认其只读 fail-closed 边界、`bootstrap_ready=true`/`supported=false` 并存、P3b 唯一 activation 和无循环。规划修订本身不授权实现、real render 或 WebUI submission；独立 PASS 前 P1 仍不得派发。
