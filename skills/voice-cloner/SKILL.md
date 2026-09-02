---
name: voice-cloner
description: Produce persisted unit voice and timing artifacts for the Mountain voice stage.
---

# Voice Cloner

从 WebUI 已保存的 `task_id`、`run_id`、AV Plan 和音色输入执行 `clone-voice`。只读取持久化参数、run-root 相对路径、结构化结果、事件和 Artifact；不从聊天或日志猜输入。

输入 Artifact：`planning.av-plan`。输出 Artifact：`audio.voice-manifest`、`timing.timeline`。每个 Voice Unit 独立产声；对齐无效时仅该 Unit 用真实音频时长等分并登记 warning/reason code，不得把 fallback 报为失败或重做其他 Unit。

```bash
python -m cli.csboard stage run --task <task-id> --run <run-id> --stage clone-voice --json
python -m cli.csboard stage retry --task <task-id> --run <run-id> --stage clone-voice --unit <unit-id> --json
```

音色、TTS、对齐和媒体服务均由持久化设置解析；Skill 不接收服务地址、密钥或文件系统路径。
