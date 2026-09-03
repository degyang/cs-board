#### CCB-TASK-CREATE-UPLOADED-PRESET-31 回执 — 2026-09-03

## §1 执行基线与变更文件

- 执行基线：`7ed128a`（接手时 HEAD；旧回执状态为“执行中”）。本轮实现提交：`7580d9a feat(mountain): complete uploaded-reference Task creation`。
- 实现范围仅为 `whiteboard + preset + uploaded-reference` 的 create-options、创建、输入原子保存与 GET 恢复；`voice-asset`、`custom-reference` 和其他 engine 均保持 `CAPABILITY_NOT_AVAILABLE`。
- 变更文件：`csboard/domain/models.py`、`csboard/adapters/filesystem/repository.py`、`csboard/application/commands.py`、`webapp/mountain_task_api.py`、`webapp/mountain_server.py`；测试为 `tests/test_task_create_contract_30.py`、`tests/test_stage_entry_contract_28.py` 及既有事务/CLI/工作单回归适配。
- 未改动 Gate、插画、媒体、Provider 或前端；正式 HTTP/OpenAPI 未公开 `execution_mode`、`manual_stages` 或自动启动入口。

## §2 §4AI 完成清单

- §4AI.2：使用生产 `start` / `_stage_response` 补齐 Artifact stale、索引存在但文件丢失、sha256 不符的三项负向证据；原有 missing reference 与 traversal 请求树快照仍使用生产 start 路径，均无 Gate 误导或副作用。
- §4AI.3：options 由 `MountainCommands.create_options()` 返回；默认值固定为 45、2、rich，voice source 有稳定 label 与 unavailable reason。
- §4AI.3：Task 持久化 `summary`、`submission_id`，旧 task.json 缺 summary 回退 title；detail/list 回读 summary。submission 索引在同进程并发下串行化，顺序重复返回同一 task/run/trace，不同 payload 返回 `SUBMISSION_CONFLICT`；Task、Run、index 三 checkpoint 任一失败均无残留。
- §4AI.3：正式 multipart 保存六 Tab 字段和上传 reference，校验 active preset 并保存稳定 ID、revision 与 style snapshot；正式真值和兼容映射（`brand_text → pen_text`、`rich → detailed`）可由 GET 恢复。分段规则固定为 `min=max(5,floor(target_chars*0.6))`、`max=min(500,max(target_chars*2,target_chars+40))`。
- §4AI.3：首次缺 reference、非法枚举/边界、不可用来源或 style 失败时保持既有 manifest/reference/Task metadata；创建成功但 inputs 失败后可使用同一 submission 重取 Task 并重试 inputs；不保存新的 execution plan，且 Run 保持 pending。
- §4AI.4：专项测试使用真实 `create_app()` HTTP、Application、Repository、线程 barrier 和 checkpoint 故障注入；没有以源码字符串、mock 调用次数或直接修改 request.json 替代目标行为。

## §3 专项测试类别、函数和数量

- 六 Tab 契约：`tests/test_task_create_contract_30.py`，22 passed；覆盖 options 注入/schema、summary/旧数据、创建边界、顺序与并发幂等、三提交点回滚、真实 preset/reference round-trip、各字段原子失败、失败恢复和不自动执行。
- Stage/Artifact 负向真值：`tests/test_stage_entry_contract_27.py`、`tests/test_stage_entry_contract_28.py`，18 passed；其中 `test_stage_response_rejects_stale_missing_or_hash_mismatched_exit_artifact` 覆盖 3 个审计阻断项。
- 输入事务、资产、服务端与 CLI 回归：`tests/test_input_transaction_11.py`、`tests/test_mountain_asset_api.py`、`tests/test_mountain_server.py`、`tests/test_cli_csboard.py`，90 passed。
- 整改后，执行计划模块级 skip 已删除。历史 execution-plan 的 API、Repository 与 CLI 行为真实执行；正式 `POST /tasks` 则严格要求 `title`、`summary`、`engine`、`pipeline_id` 和高熵 `submission_id`，不再允许以旧请求绕过正式创建边界。
- 最终 HTTP 边界整改：正式 `/inputs` signature/OpenAPI 不含、也不解析 `execution_mode/manual_stages`。新增正式 HTTP 带这两个字段的测试，证明不会产生或回读 execution plan；历史计划持久化改由 Domain/Application、Repository staging 与历史 fixture 覆盖。

## §4 全量门禁与耗时

- 整改专项：`tests/test_task_execution_plan_23.py tests/test_task_create_contract_30.py`，65 passed in 8.17s。
- 全量命令：554 passed、5 skipped、4 warnings、3 subtests passed in 102.35s，exit 0。skip 数为整改前既有基线 5；此前“42 skipped”及“47 skipped”的描述不正确，已更正。
- `/mnt/d/Workstation/Projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts` 通过。
- 两项 §4AI.5 `rg` 负向扫描通过；`git diff --check 3489a9f...HEAD` 与工作区 `git diff --check` 通过。

## §5 进程清理、clean status 和提交 hash

- 全量 pytest 与其 CLI 子进程已退出；复查无残留 pytest/`cli.csboard` 子进程。
- 本轮实现提交：`2604aed fix(mountain): close formal inputs execution boundary`。
- 报告提交见本回执写入后的独立本地提交；不推送。
- 报告提交前实现工作区 clean；报告提交后再次检查 clean status。

## §6 未完成项

无。本回执仅报告整改后的本地门禁事实；未自行宣布审核通过、CCF 联调或 `USER_ACCEPTANCE`。
