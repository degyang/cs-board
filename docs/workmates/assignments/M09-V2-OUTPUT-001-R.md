# M09-V2-OUTPUT-001-R — correct stale historical run state

状态：assigned。Owner：`backend`；工作目录：
`/mnt/d/Workstation/Projects/cs-board-worktrees/backend`。

## Evidence and goal

Independent V2 verification found that historical run
`run-m09-v2-retry-d7401b671f9941b5bd009f812df5e46b` remains `succeeded` and
contains both a final MP4 and `.remotion-private/candidate/infographic.mp4`.
That contradicts the V2 no-second-unbound-MP4 invariant and the implementation
receipt's claim that earlier attempts are failed retry history.

Correct only this stale historical run so the frozen task has exactly one
successful canonical run and no unbound historical candidate MP4. Do not
change the accepted run or its artifacts.

## Boundaries and checks

- First record hashes/status/paths for the task, accepted run and `d740…` run.
- Verify `d740…` is not `task.json.active_run_id`. Mark it failed using the
  repository/domain persistence boundary, including `render-visuals=failed`;
  do not hand-edit status JSON if a canonical API exists.
- Remove the duplicate private candidate
  `d740…/.remotion-private/candidate/infographic.mp4` after confirming its hash
  matches the already indexed final MP4. Also remove private candidate MP4s
  from failed sibling runs after recording their hashes/status and confirming
  they are not indexed artifacts. These run-private candidates are failed
  transient outputs, not accepted evidence. Do not delete any indexed artifact.
- Recompute accepted-run MP4/index/manifest hashes and real ffprobe; they must
  remain exactly `18e95359…d641a`, `47872bed…d188`, `75e30ccc…7f15`,
  1920×1080 and 2.0 seconds.
- Inspect every sibling run: only accepted `dd3…` may be succeeded; no sibling
  may retain a private candidate MP4. No new render, task, run or retry.
- No source/test/config/capability/activation/submission/service/Git changes.
- Write `docs/workmates/receipts/M09-V2-OUTPUT-001-R.md` with before/after
  evidence and `READY_FOR_INDEPENDENT_REVERIFICATION` only when all checks pass.

Do not update the main board and do not claim V2 accepted.
