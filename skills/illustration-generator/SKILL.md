---
name: illustration-generator
description: Produce or inspect Mountain illustration stage results from persisted storyboard inputs.
---

# Illustration Generator

从 WebUI 已保存的 `task_id`、`run_id` 执行 `generate-illustrations`。只读取持久化参数、run-root 相对路径、结构化结果、事件和 Artifact；不从聊天或日志猜输入。

输入 Artifact：`planning.storyboard`、`style.snapshot`。正式输出 Artifact：`illustrations.manifest`。图片 source 与 processed 成果必须分层；单个 Visual 重做只使其 clip 和最终成片失效。

当前外部 candidate Gate 尚未由 CORE 实现：不得把候选文件、手工出图或聊天附件当作正式 `illustrations.manifest`，也不得宣称 import、validate、accept、reject 或 retry 命令可执行。在该 Gate 落地前，只能报告结构化 Stage 结果或明确的能力缺口。

```bash
python -m cli.csboard stage run --task <task-id> --run <run-id> --stage generate-illustrations --json
```
