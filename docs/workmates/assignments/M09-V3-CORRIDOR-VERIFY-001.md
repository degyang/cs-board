# M09-V3-CORRIDOR-VERIFY-001 — independent boundary evidence verification

状态：assigned（2026-09-07；V2 independent V-R PASS 已由 PM 消费）
Owner：`verification`（只读）；PM 消费 verdict。

独立复核冻结 V1/V2 的版本化 input、受控 invocation、最终 MP4、ffprobe、manifest/hash/index、Task/Run/Stage 及失败/重试状态。任一缺项、不一致或不可重现均为 FAIL/BLOCKED。不得改实现、不得审计内部图片、不得改变公开 capability。

PASS 仅授权 activation ticket，不直接开放“新建任务”。

## Frozen evidence chain

- V1 accepted receipt: `docs/workmates/receipts/M09-V1-CORRIDOR-002-V-R.md`.
- V2 accepted receipt: `docs/workmates/receipts/M09-V2-OUTPUT-001-V-R.md`,
  SHA-256 `b0248d0881424d4ef0748e9c141bdaa4bbf60e0a99911a2026bf876697c239f6`.
- Canonical implementation target: `/mnt/d/workstation/projects/cs-board`;
  use the eight full source hashes in the V2 V-R receipt.
- Frozen synthetic output target:
  `/mnt/d/Workstation/Projects/cs-board-worktrees/backend/outputs/task-m09-v2-9de80fa524f54c748fea1a84d89bfa6f`;
  accepted run is `run-m09-v2-retry-dd3aeea12b1447cc84462aec253c7c63`.
- Accepted MP4/index/manifest hashes are `18e95359…d641a`,
  `47872bed…d188`, and `75e30ccc…7f15`.

## Required corridor verification

1. Establish pre/post hashes for all frozen implementation, task/run and
   accepted artifact targets. Any target drift is not a PASS.
2. Trace the saved versioned storyboard/timeline/illustration manifest and
   persistent Remotion props into the accepted renderer request boundary.
   Confirm all input references are run-contained, synthetic and correspond to
   the accepted run; do not inspect Remotion's internal image-generation logic.
3. Verify the controlled adapter contract: browser auto-resolution with the
   three browser env vars absent, bounded timeout/non-zero/empty-output failure,
   ffprobe acceptance before publish, and no residual renderer process.
4. Recompute the accepted MP4's real ffprobe, hash and size; recompute every
   indexed artifact; verify manifest bindings and relative paths.
5. Confirm the accepted Task/Run/`render-visuals` success and all failed retry
   histories are truthful, with zero private candidate MP4s.
6. Run the focused corridor tests, renderer tests/typecheck, scoped diff check,
   and a new integration-root `./scripts/workmates verify --role verification
   --evidence <new nonexistent path>` evidence file.
7. Confirm capability/create-options/public submission and activation pointer
   remain closed/absent. Do not start 8000/5182 and do not create a new render.

Write `docs/workmates/receipts/M09-V3-CORRIDOR-VERIFY-001.md` with explicit
`PASS / FAIL / MISSING EVIDENCE / BLOCKED`, criterion mapping, commands/exits,
pre/post hashes and unverified scope. Only this new receipt may be written.
