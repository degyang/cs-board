# NEXT-BE-001 — M09 当前基线门禁与激活状态核查

状态：working。Owner：backend（Codex `gpt-5.6-terra / medium`）。

## Goal

在 `/mnt/d/Workstation/Projects/cs-board-worktrees/backend`、分支 `workmates/backend`、基线 `e34ba6e83ef1a6c3ec3ad5274485505379ce0a21` 上，核对 M09 动态信息图在当前提交的真实实现、门禁、activation evidence 时效与 public submission 边界，形成可供 CC 独立复验的冻结结果。

权威输入：集成区 `docs/workmates/receipts/M09-INFRA-ACTIVATE-007-V.md`、`M09-INFRA-REAL-006-V.md`、`M09-FULL-GATE-008.md`，`docs/Mountain/29-m09-dynamic-infographic-execution-plan.md`。历史 PASS 必须按当前 HEAD 和当前时间重新判断。

## Scope / Ownership

- 只写后端 owner 范围及本 worktree 的 `docs/workmates/receipts/NEXT-BE-001.md`。
- 使用 `python3 -m venv .venv` 和 `pip install -r requirements-dev.txt` 准备独立环境；不复用集成区可写 venv。
- 先只读核对：P6 pointer/evidence 是否仍存在、24h freshness、tool/service fingerprint、九类 reason、activation projection，以及非 internal 调用是否始终拒绝。
- 运行 activation/M09 专项测试和 `scripts/run_backend_test_gate.py`。不执行真实 Remotion render，不调用图片/TTS，不刷新或伪造 P6 evidence。
- 若当前代码存在被测试或最小反证证明的缺陷，可做最小修复并补回归；否则不制造变更。
- 现场 8001 已有未归属监听 PID 244089，不接管、不终止、不使用。需要服务时另行报告，由 PM 分配。
- 公共 API/CLI/WebUI submission 必须保持关闭；不改共享看板、配置或验收标准。

## Done Predicate

- 明确记录当前 `supported/available/reason_code`、P6 evidence 的 `verified_at` 与是否过期，且区分代码通过、环境 readiness、产品开放授权。
- 专项与全量后端门禁 exit 0、无 skip；若环境准备或时长阻塞，保留精确命令和失败证据，不弱化标准。
- `git diff --check` 通过；有实现改动则创建一个本地提交，无改动则记录目标 HEAD。不得 merge/push。
- 写回执，包含实际测试计数、反证、commit/diff、未验证项和 CC 复验命令。完成后停止，等待 PM。
