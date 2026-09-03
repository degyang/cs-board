#### CCB-STAGE-GATE-STATE-MACHINE-26 回执 — 2026-09-02

- 状态: 执行中；强制门禁未通过，不得宣布完成、USER_ACCEPTANCE 或联合验收。
- 起点: `9bf76f6 docs(mountain): report stage gate invariant closeout`
- implementation_commit: `d339dbd7f34b2172ec00a3bd02b3dc6d8d939557`
- 单 Stage response: `stage_run` 现在统一返回 `ok/task_id/run_id/trace_id/stage/stages_executed/results/next_stage`，成功时最多一个 Stage/result；目标执行仍不通过 targeted pipeline 补跑依赖。
- start 入口: `MountainCommands.start_run` 先读取 Task、Run、输入；合法输入只返回 `waiting-manual-trigger`、next_stage 和 gates，零 Stage 执行。HTTP handler 不再在验证前直接 409。
- Gate DTO/CAS: HTTP request 增加必填整数 `expected_revision`，拒绝 bool/负数/未知字段；Application 在决定前检查 revision。已有 Repository history/CAS 骨架保留。
- 测试: 新增 `test_stage_gates_26.py::test_single_stage_gate_blocks_without_upstream_approval`，验证未批准上游稳定阻止目标 Stage。
- 专项原始摘要: `pytest -q -rs tests/test_stage_gates_24.py tests/test_stage_gates_25.py tests/test_task_execution_plan_23.py tests/test_cli_csboard.py` → `3 failed, 55 passed in 11.96s`。
- 失败: `test_auto_start_is_fast_and_does_not_enter_pipeline` 仍期望旧 capability 错误；`test_selective_start_and_notfound_boundaries_are_side_effect_free` 仍期望历史 `manual_stages`；CLI canonical stage 测试仍期望未批准 Gate 自动通过。均未删除、skip 或放宽。
- compileall: `python -m compileall csboard webapp cli scripts` → exit 0。
- diff check: `git diff --check` → exit 0（实现提交前）。
- 全量 pytest: 未运行；专项强制门禁已失败，未伪造通过。
- §4X 未关闭: 五 Stage executor 成功/失败/skipped/CAS 完整矩阵；跨实例/跨进程锁与崩溃恢复；精确 evidence 集合；reject/redo 失效；skipped artifact；插画固定拒绝；retry/pipeline HTTP 入口；Event/Audit canary 脱敏；CLI/plan 回归契约更新。
- 扫描: 本轮尚未执行最终两项扫描。历史不可达项预期仍含 asset repository `project_id` 与 legacy ProviderFactory `create_image_model()`；正式路径零命中门禁尚未形成。
- 距离真实 MP4 E2E: 仍缺上述 Gate 状态机闭环、真实 Codex 插画候选选择、render/compose Gate、正式 WebUI 播放下载和全链脱敏证据。
