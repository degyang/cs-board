# M09-V2-OUTPUT-001-V — independent output/registration verification

状态：assigned。Owner：`verification`（只读验收，不修改实现、输出或看板）。

## Goal

独立验证 V2 是否满足 `M09-V2-OUTPUT-001.md` 的全部 Done Predicate：最终
MP4 经真实 ffprobe 验证后才被原子登记，manifest/hash/index 与磁盘一致，且
Task/Run/Stage 状态真实。不得把测试通过等同于输出验收。

## Frozen targets

- 主集成目录：`/mnt/d/Workstation/Projects/cs-board`。
- 合成输出目录：`/mnt/d/Workstation/Projects/cs-board-worktrees/backend/outputs/task-m09-v2-9de80fa524f54c748fea1a84d89bfa6f`。
- 接受候选 run：`run-m09-v2-retry-dd3aeea12b1447cc84462aec253c7c63`；其他 run 只能作为失败/retry 历史，不得替代接受候选。
- 实现文件 SHA-256：
  - `csboard/adapters/filesystem/artifacts.py` = `62071f0b2cb8dd6bfd980745f5a92e5fe1a40ef2fbbe0e48cf7a24eb1011187c`
  - `csboard/application/commands.py` = `fdf30d215ddd134c829a1e611b2e44c16a38056eda11496c9b3d8ad7b586fcdd`
  - `tests/test_infographic_routing_p4.py` = `6a2f0a533b78c2c623869d3718686050709dd61e5cf047cf98eb6a3eb1b8f76d`
  - `tests/test_infographic_e2e.py` = `0b2d23979cbbdc7bb7d66e381b432aab23d48886789a5f8868cf4fc48ff1fb95`
- V1 renderer/resolver hashes are recorded in `M09-V1-CORRIDOR-002-V-R.md` and must remain unchanged.

## Required checks

1. Pre/post hash the frozen targets and report drift.
2. Inspect the actual accepted run: exactly one final indexed MP4, no accepted-run private candidate; recompute all indexed sizes/hashes and manifest bindings; run real `ffprobe`; confirm input snapshots are synthetic and paths are run-relative.
3. Confirm accepted Task/Run/`render-visuals` succeeded only after required artifacts exist; inspect all sibling run statuses so incomplete historical attempts are not falsely successful.
4. Review the diff for rollback/failure semantics, including source confinement, empty source, index-write failure and post-probe registration failures. Run the 37-test focused gate, renderer tests/typecheck, scoped diff check, and residual-renderer-process check.
5. Run `/mnt/d/Workstation/Projects/cs-board/scripts/workmates verify --role verification --evidence <全新且不存在的本地证据路径>` from the integration root. Do not delete or reuse an old evidence file.
6. Treat the missing old P6 activation fixture as outside this V2 acceptance only after confirming no activation pointer/capability/public-submission change was made.

## Exit

Write `docs/workmates/receipts/M09-V2-OUTPUT-001-V.md` with an explicit
`PASS / FAIL / MISSING EVIDENCE / BLOCKED`, criterion-to-evidence mapping,
commands/exit codes, pre/post hashes and unverified scope. Do not modify product
files, outputs, assignments, board, services, capability, submission, or Git
history. V3 stays blocked unless this verdict is PASS and PM consumes it.
