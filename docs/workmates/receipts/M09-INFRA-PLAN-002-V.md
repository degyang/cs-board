# M09-INFRA-PLAN-002-V 独立复验回执

结论：**FAIL**。本次为只读计划核验；未修改产品代码、规划或测试，未运行 real render、未创建任务、未打开 WebUI submission。唯一写入为本回执。因此本回执**不授权**自动派发 P1。

## 已检查的输入

- `docs/workmates/assignments/M09-INFRA-PLAN-002.md`
- `docs/workmates/receipts/M09-INFRA-PLAN-002.md`
- `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md`
- 两份既有 29 计划：`29-voice-provider-and-infographic-plan.md`、`29-m09-infographic-work-breakdown.md`

静态检查使用 `nl -ba`、`rg` 和 `git diff --check`；后者退出码为 0。没有运行测试，以避免产生缓存或状态变更。

## 逐项核验

1. **PASS — P3/P6 的主依赖图与 next queue 无循环。**
   - P6 的 entry 明确为 P1、P2、P3a、P4、P5 全部 exit，且不依赖 P3b（计划第 115–123 行）。
   - P3b 只在 P6 独立复核成功 evidence 后 activation（第 137–144 行）。第 125–135 行的图和说明均为 `P1 → (P2 || P3a) → P4 → P5 → P6 → P3b`，不存在 P3a/P3b 到 P6 的回边。
   - 第 184–192 行满足 PLAN-002 指定的 P1-first 自动队列：P1 PASS 后 P2/P3a 并行，随后 P4→P5→P6→P3b。

2. **PASS — create-options 的真实开放条件、fail-closed 行为和 reason codes 已明确。**
   - 第 141 行将 `available=true/supported=true` 精确绑定为：当前 pre-smoke readiness、非空真实 MP4、有效 ffprobe、artifact index 与 render manifest 及声明 hash 一致、evidence 新鲜、独立复核通过；任一不成立即 false/unavailable。
   - 第 152 行定义稳定优先 reason codes：`BOOTSTRAP_NOT_READY`、`REAL_SMOKE_EVIDENCE_REQUIRED`、`EVIDENCE_INVALID`、`EVIDENCE_EXPIRED`、`EVIDENCE_NOT_INDEPENDENTLY_VERIFIED`，并规定 `verified_at` 起 24 小时 freshness，以及工具/lockfile/renderer/props hash、browser identity、service probe 或 external gate 变化立即失效。

3. **PASS — P4 受控 internal/test 通道没有被等同于用户提交。**
   - P4 第 103–104 行明定即使合流成功也只允许 internal/test，不能让 `create-options` available，不能开启用户/API/WebUI 提交。
   - P6/P3b 第 117–123、139–144 行也分别禁止 WebUI 与自动开启提交。

4. **PASS — P1–P5、legacy separation 和 task-package 规则未被削弱。**
   - P1/P2/P4/P5 的边界、entry/exit、测试与禁止项保留于第 70–113 行；legacy read-only 与 anti-fallback 规则见第 156–162 行；原子 artifact index、manifest/hash、恢复与清理规则见第 164–178 行。

5. **FAIL — P3a 的架构职责自相矛盾，无法作为可执行的实现/验证票。**
   - 第 64 行将 P3a 定义为检查「Node、脚本、锁定依赖、浏览器、FFmpeg/ffprobe」等工具链 readiness。
   - 但 P3a 工作包第 88–95 行称其为「非 renderer」，第 90 行禁止检查 renderer-specific readiness，第 94–95 行又明确 P3a exit 不声明 Node、Remotion、browser、FFmpeg、ffprobe、render script 或 adapter 可用，并禁止「检查 renderer/toolchain」。
   - 这与 PLAN-002 要求的 P3a「工具链/服务/配置/浏览器/FFmpeg readiness」直接冲突，也使 P3a 的 reason-code matrix、P4 合流输入和 P6 entry 无法由独立验证者一致判定。虽然 DAG 已解除循环，架构/工作包/验证标准仍非单一真源，不能安全自动派 P1。

## 必须纠正后再复验

在 `29-m09-dynamic-infographic-execution-plan.md` 统一 P3a 的责任边界：要么让 P3a 明确实际检查并产出 Node/script/lockfile/browser/FFmpeg/ffprobe 的 bootstrap/toolchain 诊断和 reason matrix；要么把这些明确归入一个独立、可追溯的 P2/P4 readiness contract，并同步改正第 64 行、P3a entry/exit、P4 合流、P6 entry 和 reason-code 归属。不得同时要求和禁止 P3a 检查同一类条件。

修正并再次取得独立 **PASS** 前，保持 capability `available/supported=false`，不得自动派发 P1 或开放任何用户提交。
