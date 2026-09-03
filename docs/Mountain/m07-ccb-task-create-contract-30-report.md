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
- 指定专项总计：130 passed，23.27s。历史 `auto/selective` 策略测试为 42 skipped，理由为第一阶段六 Tab 正式路径明确排除该能力；遗留 request 仍可只读兼容。

## §4 全量门禁与耗时

- 指定专项命令（§4AI.5）：130 passed in 23.27s。
- 全量命令：511 passed、47 skipped、4 warnings、3 subtests passed in 92.14s（外层 wall time 94.18s，exit 0）。
- `/mnt/d/Workstation/Projects/cs-board/.venv/bin/python -m compileall csboard webapp cli scripts` 通过。
- 两项 §4AI.5 `rg` 负向扫描通过；`git diff --check 3489a9f...HEAD` 与工作区 `git diff --check` 通过。

## §5 进程清理、clean status 和提交 hash

- 全量 pytest 与其 CLI 子进程已退出；复查无残留 pytest/`cli.csboard` 子进程。
- 实现提交：`7580d9a feat(mountain): complete uploaded-reference Task creation`。
- 报告提交见本回执写入后的独立本地提交；不推送。
- 报告提交前实现工作区 clean；报告提交后再次检查 clean status。

## §6 未完成项

无。本回执仅报告 CCB-TASK-CREATE-UPLOADED-PRESET-31 的实现与本地门禁事实；未自行宣布独立审核通过，亦未宣布 `USER_ACCEPTANCE`。
