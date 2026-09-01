# M04 Audit — PR-1: Pipeline 编排 + CLI 补全

**Date:** 2026-08-29
**Scope:** PipelineOrchestrator、CLI 命令补全、项目请求存储
**Status:** ✅ Complete

---

## Deliverables

### 1. PipelineOrchestrator (`csboard/application/pipeline.py`)

| Aspect | Details |
|--------|---------|
| 阶段依赖图 | `segment-script → clone-voice → plan-storyboard → generate-illustrations → render-visuals → compose-video` |
| 策略 | `auto`（运行到完成）、`gated`（每阶段后暂停）、`targeted`（运行指定阶段） |
| 恢复 | `resume_pipeline()` 从最后成功的阶段继续 |

**关键行为：**
- `get_next_stage(run)` — 返回下一个待执行阶段
- `get_pending_stages(run, target)` — 返回到达目标阶段所需的待执行阶段列表
- `run_pipeline()` — 按策略执行阶段，失败时停止，gated 时暂停
- `resume_pipeline()` — 恢复失败或中断的流水线
- `register_stage(name, executor)` — 注册阶段执行器
- 未注册的阶段返回 `CAPABILITY_NOT_AVAILABLE` 错误

### 2. MountainCommands 扩展 (`csboard/application/commands.py`)

**新增方法：**

| 方法 | 功能 |
|------|------|
| `artifact_show()` | 返回指定 artifact 的内容（JSON 解析后返回） |
| `stage_retry()` | 重试指定阶段，支持 `--unit`/`--visual` 作用域，自动标记下游阶段为 stale |
| `pipeline_run()` | 运行流水线，委托给 PipelineOrchestrator |
| `pipeline_resume()` | 恢复流水线 |
| `_exec_segment_script()` | 阶段执行器：从项目请求读取 script |
| `_exec_clone_voice()` | 阶段执行器：从项目请求读取 reference_audio、tts_url 等 |
| `_read_request()` | 读取项目 request.json |

**项目请求存储：**
- `create_project()` 现在接受 `request` 参数并存储到 `project.json`
- PipelineOrchestrator 通过 `_read_request()` 读取请求获取阶段输入

### 3. CLI 补全 (`cli/csboard.py`)

**新增命令：**

| 命令 | 参数 |
|------|------|
| `artifact show` | `--project`, `--run`, `--key` |
| `pipeline run` | `--project`, `--run`, `--policy`, `--stage`, `--events jsonl` |
| `pipeline resume` | `--project`, `--run`, `--policy`, `--events jsonl` |
| `stage retry` | `--project`, `--run`, `--stage`, `--unit`, `--visual` |
| `logs tail --follow` | 持续输出新日志 |

**stage run 路由逻辑：**
- `segment-script` 和 `clone-voice` 走原有实现
- 已注册的其他阶段走 pipeline targeted 模式
- 未注册的阶段抛出 `CAPABILITY_NOT_AVAILABLE`

---

## Tests

### `tests/test_pipeline_orchestrator.py` (23 tests)

| Test class | Count | Coverage |
|-----------|-------|----------|
| `TestStageOrder` | 3 | 阶段数量、首尾阶段 |
| `TestGetNextStage` | 4 | 全待执行、部分完成、全部完成、失败阶段 |
| `TestGetPendingStages` | 4 | 全待执行、部分完成、目标限制、全部完成 |
| `TestRunPipeline` | 7 | auto/gated/targeted 策略、无效策略、未注册阶段、阶段失败停止 |
| `TestResumePipeline` | 2 | 从失败恢复、已完成无需恢复 |
| `TestNextStageAfter` | 3 | 首阶段、末阶段、未知阶段 |

### `tests/test_cli_csboard.py` (8 tests, +4 新增)

| Test | Coverage |
|------|----------|
| `test_artifact_show_returns_content` | artifact show 返回内容 |
| `test_artifact_show_missing_key` | 缺失 artifact 返回 NOT_FOUND |
| `test_pipeline_run_gated_policy` | pipeline gated 策略执行 |
| `test_stage_retry_missing_stage_returns_not_found` | 未注册阶段返回 NOT_FOUND |

---

## 端到端验证

```bash
# 创建项目
python -m cli.csboard project create --title "测试" --json
# → ok: true, project_id, run_id, trace_id, command_id

# 运行 segment-script
python -m cli.csboard stage run --project <id> --run <run-id> --stage segment-script --script "第一句。第二句。" --json
# → ok: true, artifacts: ["planning.av-plan"]

# 查看 artifact
python -m cli.csboard artifact show --project <id> --run <run-id> --key planning.av-plan --json
# → ok: true, content: {voice_units: [...], ...}

# 运行 pipeline (gated)
python -m cli.csboard pipeline run --project <id> --policy gated --json
# → ok: true, policy: "gated", stages_executed: ["segment-script"]

# 未注册阶段
python -m cli.csboard stage run --project <id> --stage plan-storyboard --json
# → ok: false, error.code: "CAPABILITY_NOT_AVAILABLE"
```

---

## Files added/modified

| File | Action |
|------|--------|
| `csboard/application/pipeline.py` | Created (220 lines) |
| `csboard/application/commands.py` | Modified (+120 lines: artifact_show, stage_retry, pipeline_run/resume, stage executors) |
| `cli/csboard.py` | Modified (+80 lines: artifact, pipeline, stage retry, logs follow) |
| `tests/test_pipeline_orchestrator.py` | Created (23 tests) |
| `tests/test_cli_csboard.py` | Modified (+4 tests) |

---

## Test results

```
Ran 131 tests in 0.561s — OK (skipped=4)
```

所有测试通过。4 个跳过是由于缺少可选依赖（httpx, starlette, jsonschema）。
