---
name: visual-renderer
description: Render persisted accepted Mountain illustrations into visual clips.
---

# Visual Renderer

从 WebUI 已保存的 `task_id`、`run_id` 执行 `render-visuals`。只读取持久化参数、run-root 相对路径、结构化结果、事件和 Artifact；不从聊天或日志猜输入。

输入 Artifact：`illustrations.manifest`、`timing.timeline`、`planning.storyboard`。输出 Artifact：`render.manifest`。只使用已验收插画和 Timeline 时长；不得重跑对齐或重新估算 Voice 时长，不得执行最终音画合成。

```bash
python -m cli.csboard stage run --task <task-id> --run <run-id> --stage render-visuals --json
python -m cli.csboard stage retry --task <task-id> --run <run-id> --stage render-visuals --visual <visual-id> --json
```
