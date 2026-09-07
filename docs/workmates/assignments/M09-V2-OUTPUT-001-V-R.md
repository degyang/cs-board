# M09-V2-OUTPUT-001-V-R — independent correction re-verification

状态：assigned。Owner：`verification`（只读；只写本任务回执）。

Re-assess V2 after `M09-V2-OUTPUT-001-R`. The first verifier's PASS was not
consumed because its own evidence showed one stale succeeded sibling and an
unbound private candidate, contradicting the original V2 invariants.

## Frozen correction state

- Output root: `/mnt/d/Workstation/Projects/cs-board-worktrees/backend/outputs/task-m09-v2-9de80fa524f54c748fea1a84d89bfa6f`.
- `task.json` = `f02c10de8ca62ae458ec2f754fd5c4969264e515243c0ff85dc03465d32ba044`.
- Sibling `run.json` hashes:
  - `987…` = `0661196e…1415`
  - `23a9…` = `4c0aba80…5c0ac1`
  - `d740…` = `d9f67e48…91f3f0`
  - accepted `dd3…` = `952437ed…04ae91e`
  - `eedf…` = `9550f000…63224`
- Accepted MP4/index/manifest remain `18e95359…d641a`, `47872bed…d188`,
  `75e30ccc…7f15`.
- Source/test hashes remain those in `M09-V2-OUTPUT-001-V.md`.

## Required checks

1. Pre/post verify all full hashes above and the implementation/V1 hashes.
2. Confirm accepted `dd3…` is the only succeeded run and only active run;
   every sibling is failed with `render-visuals=failed`.
3. Confirm zero `.remotion-private/candidate/*.mp4` files across all siblings,
   while all indexed artifacts remain present and hash/size-valid.
4. Repeat real ffprobe and accepted manifest/index/hash/path checks.
5. Repeat focused 37 tests, renderer 3 tests/typecheck, scoped diff check,
   residual-process check, and fresh project-root Workmates verify evidence.
6. Confirm no new task/run/render, activation, capability or submission change.

Write `docs/workmates/receipts/M09-V2-OUTPUT-001-V-R.md` with explicit verdict,
criterion mapping, commands/exits, full pre/post hashes, and unverified scope.
Do not modify outputs, implementation, assignment, board, services or Git.
