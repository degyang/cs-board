# ASSET-PROV-FE-002-V — 当前资产发现前端独立验证

状态：done（2026-09-06 PM consumed PASS）
Owner：verification（Claude Code `mimo-v2.5-pro / medium`）
模式：read-only independent verification

## Frozen target

- 实现工作区：`/mnt/d/Workstation/Projects/cs-board-worktrees/frontend`
- 实现回执：`docs/workmates/receipts/ASSET-PROV-FE-002.md`（在上述 frontend worktree）
- 机器可读证据：`docs/workmates/evidence/ASSET-PROV-FE-002.json`（在上述 frontend worktree）
- 目标 diff SHA-256：`e8f0c5f2509d4a35f0de995946fd281b9755ab0a1915e0ac6dddc47e43f9130f`
- 哈希范围：回执列出的八个 frontend implementation/test paths；新增文件按 `/dev/null` no-index diff 计入。

## Authority and scope

1. `AGENTS.md`
2. `docs/workmates/assignments/ASSET-PROV-FE-002.md`
3. `docs/Mountain/30-artifact-provenance-and-regeneration.md`
4. `docs/workmates/receipts/ASSET-PROV-BE-003-V.md`

Only inspect the frozen frontend worktree and run read-only tests/builds. Do not
modify frontend/backend implementation, existing tests, task standards, the
shared board, or EnvOps-managed topology. Do not commit or push. You may write
only this new verification receipt in the integration control plane:
`docs/workmates/receipts/ASSET-PROV-FE-002-V.md`.

## Required checks

- Recompute the stated target hash before and after verification. A mismatch is
  `FAIL` / `MISSING EVIDENCE`; do not verify a drifting target.
- Independently inspect the client request: it must use the task/run list URL,
  encode identities, consume the server `media_url`, and never derive IDs,
  kinds, URLs or filesystem paths from legacy artifacts.
- Independently run the focused three test files, the complete frontend test
  suite, `npm --prefix web-v2 run build`, and `git diff --check` from the
  frontend worktree. Record exact outcomes, warnings/skips, and duration.
- Confirm image/audio/video, loading, empty, sanitized 4xx/network failure,
  legacy-artifact-empty + current-assets-nonempty, and route-switch late
  response behavior are covered and behaving as claimed. Confirm configuration
  accessibility/sanitization remains intact and “再次生成” remains disabled.
- Treat the failed `workmates verify` evidence registration as an environment
  observation: reproduce only if safe, report the duplicate-worktree-path
  result, and do not repair the managed topology. It is not permission to waive
  the actual frontend gates.

## Verdict and stop condition

Write PASS, FAIL, MISSING EVIDENCE, or BLOCKED with the criterion-to-evidence
mapping and pre/post hashes. Stop immediately after the receipt; PM alone makes
stage acceptance.
