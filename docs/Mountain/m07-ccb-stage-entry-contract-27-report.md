#### CCB-STAGE-ENTRY-CONTRACT-27 回执 — 2026-09-03

- 状态: 完成当前 §4AA 切片；不代表后续 Gate 状态机、插画候选、媒体 E2E、USER_ACCEPTANCE 或联合验收通过。
- 起点: `d6ffd93 docs(mountain): report manual gate state machine`
- implementation_commit: `71f198b4f14552b1ca3d19ffe7db2e039f4a2ce4`
- start 验证顺序: Application 先读取 Task、Run 并验证归属，再验证持久化 request 的非空、script 字符串及最小长度；不存在为 404 `NOT_FOUND`，缺输入/无效文案为 400 `VALIDATION_ERROR`。
- start 零副作用: 合法输入只返回 `ok/state=waiting-manual-trigger/task_id/run_id/trace_id/next_stage/gates`；不调用 capability resolver、Pipeline 或 Stage。`test_start_has_not_found_invalid_input_and_waiting_boundaries` 对 run.json 字节快照证明零写入。
- 单 Stage schema: 固定 builder 返回 `ok/task_id/run_id/trace_id/stage/stages_executed/results/next_stage/next_action`；executor result 不再覆盖 envelope。executor 被调用时 `stages_executed` 与 `results` 各恰一项；失败无可前进 next_stage。
- 四项旧回归的权威断言: execution-plan auto start 现断言 waiting 且 resolver 零调用；selective start 断言 Gate view；CLI 第一阶段仅 anchors 可执行，其余未批准上游稳定 `STAGE_GATE_REQUIRED`；Mountain server start 断言 waiting 而非缺服务错误。
- 新测试: `tests/test_stage_entry_contract_27.py` 覆盖 HTTP start 404、400、200 与 run 状态零副作用。
- 专项 pytest: `80 passed in 15.59s`。
- 全量 pytest: `514 passed, 5 skipped, 4 warnings, 3 subtests passed in 94.72s`，exit 0；warnings 为现有 jsonschema `RefResolver` deprecation。
- compileall: `python -m compileall csboard webapp cli scripts` exit 0。
- 正式路径扫描: `! rg -n "(/projects|project_id|create_image_model\\()" ...` exit 0。
- diff check: `git diff --check` exit 0。
- 保留缺口: 并发/CAS 崩溃恢复、reject/redo 精确失效、skipped Artifact、插画固定拒绝与候选流程、Event/Audit canary 脱敏仍属于后续独立 Gate 切片，未在本轮扩展。
