---
name: visual-anchor-generator
slug: visual-anchor-generator
description: Generate visual anchors from the persisted Task preparation for the first Mountain stage.
---

# Visual Anchor Generator

从 WebUI 已保存的 `task_id`、`run_id` 和持久化文案整理结果执行 `generate-visual-anchors`。只读取持久化参数、run-root 相对路径、结构化结果、事件和 Artifact；不从聊天或日志猜输入。

输入 Artifact：`planning.av-plan` 的已保存文案整理/锚定设置。输出 Artifact：`planning.av-plan`。不得改写 Voice Unit、范围或顺序；锚定关闭时登记确定性 skipped/default 结果。

```bash
python -m cli.csboard stage run --task <task-id> --run <run-id> --stage generate-visual-anchors --json
```

失败时读取结构化错误和事件；不要补传文案、Provider 参数或路径。
