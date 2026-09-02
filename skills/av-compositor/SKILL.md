---
name: av-compositor
description: Compose persisted Mountain voice and render artifacts into the final video stage.
---

# AV Compositor

从 WebUI 已保存的 `task_id`、`run_id` 执行 `compose-video`。只读取持久化参数、run-root 相对路径、结构化结果、事件和 Artifact；不从聊天或日志猜输入。

输入 Artifact：`audio.voice-manifest`、`timing.timeline`、`render.manifest`。输出 Artifact：`output.final-manifest`（及其正式视频成果）。字幕不得跨 Voice Unit；Voice 与 Visual 必须稳定且恰好使用一次。只有结构化质量结果 `validation.passed=true` 才能报告完成。

```bash
python -m cli.csboard stage run --task <task-id> --run <run-id> --stage compose-video --json
python -m cli.csboard artifact show --task <task-id> --run <run-id> --key output.final-manifest --json
```
