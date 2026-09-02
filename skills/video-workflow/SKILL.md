---
name: video-workflow
description: Inspect, resume, and coordinate a persisted Mountain Task through the cs-board CLI.
---

# Video Workflow

起点是 WebUI 已创建并保存输入的 `task_id` 与 `run_id`。本 Skill 不创建任务、不收集文案或音色、不接收 request JSON，也不从聊天或日志猜输入。只读取持久化参数、run-root 相对路径、结构化结果、事件和 Artifact。

它只编排六个规范 Stage：`generate-visual-anchors`、`clone-voice`、`plan-storyboard`、`generate-illustrations`、`render-visuals`、`compose-video`。运行和恢复应尊重持久化 execution plan；遇到人工或外部 Gate 时报告结构化等待状态，不能假装成功或自行绕过。

```bash
python -m cli.csboard pipeline run --task <task-id> --run <run-id> --policy auto --json
python -m cli.csboard pipeline resume --task <task-id> --run <run-id> --json
python -m cli.csboard task show --task <task-id> --json
python -m cli.csboard run trace --task <task-id> --run <run-id> --json
python -m cli.csboard events list --task <task-id> --run <run-id> --after <cursor> --json
```

外部插画 Gate 的 Work Order/import/accept 命令尚未实现；仅报告其状态和缺口，不发明 CLI。
