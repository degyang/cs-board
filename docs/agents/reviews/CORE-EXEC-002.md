# CORE-EXEC-002 Review

- Reviewer: PM (`/root/pm`)
- Delivery: `ea7b54f`
- Base: `a5d5938`
- Final verdict: **APPROVED**
- Next attempt: 2

## 已验证

- 独立复现任务定向测试：`103 passed`；
- persisted `ExecutionPlan`、manual gate、resume、targeted 前置门禁、inputs 回读与 task lock 的主体实现成立；
- 变更没有进入 Work Order、WebUI 或 Legacy 扩张范围。

## 必须纠正的问题

`cli/csboard.py` 仍暴露 `--script`、`--reference`、`--tts-url`、`--tts-mode`。其中
`stage run clone-voice` 继续以 `not args.reference` 拒绝执行，并在进入统一
`commands.stage_run(...)` 前构造未被使用的 IndexTTS、Whisper、FFmpeg adapter；其他媒体 Stage
也保留相同类型的无效构造。

这使 CLI 仍把聊天期/临时参数当作执行输入，违反本任务第 6 条“Application、API、CLI 读取同一
persisted plan”，也违反已冻结 Work Order 消费边界“不再索取 `--reference`、`--tts-url` 等参数”。
现有 103 个测试没有覆盖这一真实 CLI 参数边界。

## 有界返工范围

只统一 CLI stage dispatch、移除旧 stage 制作参数和未使用 adapter 构造，并添加六阶段 CLI
subprocess 行为测试。不得推翻已通过的 Application/API 实现，不得进入 Work Order。

## 复核命令

```bash
/mnt/d/workstation/projects/cs-board/.venv/bin/python -m pytest -q \
  tests/test_task_execution_plan_23.py \
  tests/test_pipeline_orchestrator.py \
  tests/test_cli_csboard.py \
  tests/test_mountain_contracts.py \
  tests/test_mountain_server.py
# 结果：103 passed, 2 warnings

rg -n -- '--script|--reference|--tts-url|--tts-mode|IndexTTSAdapter|WhisperAlignmentAdapter|FFmpegMediaAdapter' cli/csboard.py
```

## Attempt 2 final review

- Delivery: `e1bc3d5`（code commit `e6349e9` + report commit）；
- diff 仅涉及 `cli/csboard.py`、`tests/test_cli_csboard.py` 和原交付报告；
- `stage run --help` 仅保留 `--task`、`--run`、`--stage`、`--events`；
- 六个规范 Stage 统一走 persisted-plan dispatch；`clone-voice` 不再要求第二份 reference；
- stage dispatch 中未使用的 IndexTTS、Whisper、Whiteboard、FFmpeg adapter 构造已移除；
- 独立定向门禁：`106 passed, 2 warnings`；`git diff --check` 通过。

Attempt 1 的问题和证据保留在上文；attempt 2 已完成有界纠偏，没有进入 Work Order 或 WebUI。
本裁决不授权合并。
