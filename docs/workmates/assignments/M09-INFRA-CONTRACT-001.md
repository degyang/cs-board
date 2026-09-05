# M09-INFRA-CONTRACT-001 — P1 动态信息图契约与 fixture

`worker_backend`（Codex medium），执行 P1，且仅执行 P1 的领域/props/任务包契约冻结。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

依据：已独立 PASS 的 `M09-INFRA-PLAN-003-V.md` 与 `docs/Mountain/29-m09-dynamic-infographic-execution-plan.md` P1。

回执：`docs/workmates/receipts/M09-INFRA-CONTRACT-001.md`

允许范围：`csboard/domain/infographic.py`、紧邻的 domain schema/validation 或 port type、`video_renderer/src/types.ts`、直接 P1 fixtures/tests。只在 P1 契约必要时触及 task-package schema type；不得改 pipeline、commands/API/CLI、renderer adapter 实现、capabilities、legacy/webapp、预置音色或动态信息图 WebUI。

必须完成：

1. 将 `InfographicStoryboard v1`、`DynamicInfographicProps v1`、render-manifest/evidence schema 固化为版本化、纯领域/props 契约；明确 field name、schema version、稳定 ID、时间/帧坐标与 run-relative artifact reference 语义。
2. 决定并记录每 Voice Unit 的页面策略（1–2 页或固定策略），并在 schema/fixture 中消除当前 1 页草案与 WBS 的歧义。
3. 验证并拒绝空/重叠/零时长、未知 node kind、丢失 visual ref、非稳定 ID 或绝对路径/secret；domain 不得 import Remotion、subprocess、webapp 或 provider。
4. 产出黄金 JSON fixtures，覆盖空/单/多 visual、页面/节点/cue 时序、frame conversion、schema round-trip；`DynamicInfographicProps` fixture 必须通过 TypeScript typecheck。
5. 明确 P1 render manifest/evidence 的最小字段，供 P2/P6 使用，但不得创建 render、MP4、任务或 capability activation。

门槛：新增/受影响 P1 tests、相关 domain suite及 `video_renderer` TypeScript typecheck 均退出 0；回执列出命令、退出码、pass/fail/skip、耗时、diff 文件边界和 P2/P3a 的未授权项。不得自行验证/接受、不提交/推送、不加 skip。

出口：`READY_FOR_INDEPENDENT_P1_VERIFICATION`。P2/P3a 仅在独立 P1 PASS 后由 PM 派发。
