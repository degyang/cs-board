---
name: visual-anchor-generator
description: bad self-cycle fixture
---

输入 Artifact：`planning.av-plan`。输出 Artifact：`planning.av-plan`。
只读取 task_id、run_id、相对路径、结构化结果、Artifact。
python -m cli.csboard stage run --task <task-id> --run <run-id> --stage generate-visual-anchors --json
