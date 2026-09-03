#### CCB-STAGE-ENTRY-TRUTH-28 回执 — 2026-09-03

- 状态: 完成当前 §4AC 切片；不代表后续 Gate 状态机、插画候选、媒体 E2E、USER_ACCEPTANCE 或联合验收通过。
- 起点: `3dc602a docs(mountain): report manual stage entry contract`
- implementation_commit: `7ffd560522168b6b5a855a447bfc4516429583be`
- 必要输入验证: 统一 `_validate_start_inputs` 验证 script 类型及最小长度、reference_audio 的相对 `inputs/` 路径、文件存在和非空；绝对路径与 traversal 均只返回安全 `invalid_fields`，不泄漏物理路径。
- 输入矩阵: 缺 script/短 script/缺 reference/缺文件/空文件/绝对路径/`..` 均为 `400 VALIDATION_ERROR`；Task/Run 不存在或归属冲突仍为 `404 NOT_FOUND`。合法 start 通过正式 multipart upload 保存非空 WAV。
- 零副作用: `test_start_has_not_found_invalid_input_and_waiting_boundaries` 保持 run.json 字节快照；execution-plan 的既有 task 目录 snapshot 回归继续通过。合法 start 不解析 resolver、不运行 Pipeline/Stage，也不写 Gate、Artifact、Event 或 Audit。
- 单 Stage response: 唯一 `_stage_response` 负责 envelope；executor 身份字段若与 task/run/trace/stage 冲突，返回稳定 `STAGE_RESPONSE_IDENTITY_CONFLICT` 结果而不泄漏冲突值。
- response/next-action: succeeded/skipped 仅在完整出口 Artifact 验证且 Gate 已持久化 `waiting-review` 时返回 `GATE_REVIEW_REQUIRED`；compose-video 同样适用。出口无效返回 `STAGE_OUTPUT_INVALID`、无 next_stage；failed 返回单项已执行 result、`ok=false`、next_stage null 与 `FIX_STAGE_RESULT`。
- API 文档: `m07-phase-one-task-gate-api.md` 已冻结 start 输入/error 与单 Stage response/next-action 规则。
- 新测试: `tests/test_stage_entry_contract_28.py` 使用真实 router 覆盖缺 reference 与 traversal；§4AA tests 覆盖合法 multipart start。现有 CLI、server、plan 测试更新为必要音频和手工 Gate 权威语义。
- 专项 pytest: `81 passed in 14.72s`。
- 全量 pytest: `515 passed, 5 skipped, 4 warnings, 3 subtests passed in 106.34s`，exit 0；warnings 为既有 jsonschema RefResolver deprecation。
- compileall: exit 0；正式路径静态扫描 exit 0；`git diff --check` exit 0。
- 后续冻结缺口: 并发/CAS 崩溃恢复、reject/redo 失效、skipped Artifact、插画固定拒绝/候选契约和 Event/Audit canary 脱敏不在本轮范围，未继续实现。
