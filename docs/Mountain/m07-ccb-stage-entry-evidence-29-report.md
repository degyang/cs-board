#### CCB-STAGE-ENTRY-EVIDENCE-29 回执 — 2026-09-03

- 状态: 完成 §4AE 真实行为证据切片；不代表后续 Gate/CAS、插画候选、媒体 E2E、USER_ACCEPTANCE 或联合验收通过。
- 起点: `a74898d docs(mountain): report stage entry response truth`
- implementation_commit: `1e6b330e7d9ae51bbc40f1df5403542aec1a7257`
- 输入矩阵证据: `test_start_rejects_missing_reference_and_unsafe_reference`、`test_start_input_matrix_has_no_task_tree_side_effects` 覆盖缺 reference、traversal、缺 script、短 script、缺文件与绝对路径；每项断言 `400 VALIDATION_ERROR`、安全 `invalid_fields` 和无物理路径回显。合法 multipart reference 由 `test_start_has_not_found_invalid_input_and_waiting_boundaries` 保存。
- 全目录零副作用: `_snapshot()` 遍历 Task 目录全部文件，记录相对路径与 SHA-256；所有 start 输入边界请求前后断言相同，覆盖 inputs、run、artifact index、observability 与 Gate 文件。
- response 矩阵: `test_valid_outputs_require_review_even_final_stage` 覆盖 succeeded、skipped 与 compose succeeded；仅在真实 Artifact index/文件/hash 有效且 Gate 持久化 waiting-review 后返回 `GATE_REVIEW_REQUIRED`，compose `next_stage=null`。
- 失败真值: `test_invalid_output_failed_identity_and_gate_write_failure_are_safe` 覆盖出口缺失的 `STAGE_OUTPUT_INVALID`、executor failed 的单项 executed result 与 `FIX_STAGE_RESULT`、身份冲突和 Gate 持久化失败。
- 最小生产修正: identity conflict 的嵌套 result 现由服务端规范 task/run/trace/stage，并包含稳定 `STAGE_RESPONSE_IDENTITY_CONFLICT`；`mark_gate_waiting` I/O 失败转换为 `STAGE_GATE_PERSIST_FAILED`，不再谎报 review success。
- 专项 pytest: `89 passed in 15.25s`。
- 全量 pytest: `523 passed, 5 skipped, 4 warnings, 3 subtests passed in 113.48s`，exit 0；warnings 为既有 jsonschema RefResolver deprecation。
- compileall: exit 0；正式路径静态扫描 exit 0；`git diff --check a74898d...HEAD` exit 0。
- 保留缺口: Gate 并发/CAS 崩溃恢复、reject/redo 精确失效、skipped Artifact、插画候选/固定拒绝及 Event/Audit canary 脱敏均未在本轮继续实现。
