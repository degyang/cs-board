---
name: illustration-generator
description: bad retry fixture
---

输入 Artifact：`planning.storyboard`、`style.snapshot`。输出 Artifact：`illustrations.manifest`。
只读取 task_id、run_id、相对路径、结构化结果、Artifact。当前外部 candidate Gate 尚未由 CORE 实现。
python -m cli.csboard stage run --task <task-id> --run <run-id> --stage generate-illustrations --json
python -m cli.csboard stage retry --task <task-id> --run <run-id> --stage generate-illustrations --visual <visual-id> --json
