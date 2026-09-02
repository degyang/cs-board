---
name: storyboard-planner
description: Plan storyboard visuals from persisted Mountain AV and timing artifacts.
---

# Storyboard Planner

从 WebUI 已保存的 `task_id`、`run_id` 执行 `plan-storyboard`。只读取持久化参数、run-root 相对路径、结构化结果、事件和 Artifact；不从聊天或日志猜输入。

输入 Artifact：`planning.av-plan`、`timing.timeline`、`style.snapshot`。输出 Artifact：`planning.storyboard`。不得改变 Unit/Visual 的原文、数量、顺序、范围或时间边界；只补充构图、prompt、overlay 和 shot 计划。

```bash
python -m cli.csboard stage run --task <task-id> --run <run-id> --stage plan-storyboard --json
python -m cli.csboard artifact show --task <task-id> --run <run-id> --key planning.storyboard --json
```
