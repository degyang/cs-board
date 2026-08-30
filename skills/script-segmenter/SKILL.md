---
name: script-segmenter
description: Segment narration script into Voice Units and Visual Items for video production. Use for the first stage of the standard pipeline.
---

## 输入与输出

- 输入：Project、原始文案、分割策略版本和系统级 TTS 能力限制；
- 输出：`planning.av-plan`、Voice Unit/Visual Item 摘要、覆盖率和规划告警。

## 强制规则

- 先按语义完整性、内容结构和 TTS 能力决定 Voice Unit；
- 再在每个 Unit 内决定一个或多个 Visual Item 及连续原文范围；
- 2–3 句话、1–2 张图只是常见目标，不是硬限制；
- 不生成 Voice、图片构图或毫秒时间，不改写旁白；
- 原文覆盖率不是 100%、范围重叠或越界时失败；
- 重跑导致稳定 ID 或文字范围变化时，使全部下游失效。

## CLI 命令

```bash
# 运行文案分割
python -m cli.csboard stage run --task <id> --run <run-id> --stage segment-script --script "旁白文案" --json

# 查看生成的 AV Plan
python -m cli.csboard artifact show --task <id> --run <run-id> --key planning.av-plan --json
```

## 输出格式

成功时返回：

```json
{
  "ok": true,
  "command": "stage.run",
  "task_id": "project-xxx",
  "run_id": "run-xxx",
  "stage": "segment-script",
  "result": "succeeded",
  "artifacts": ["planning.av-plan"],
  "next_stage": "clone-voice"
}
```

## 与其他 Skill 的协作

- **上游**：video-workflow 创建任务并提供文案
- **下游**：voice-cloner 使用 av-plan 生成语音

## 错误处理

- 文案为空或缺失 → `VALIDATION_ERROR`
- 覆盖率不是 100% → `SEGMENTATION_COVERAGE_INVALID`
- 任务 pipeline 不是 mountain-av-v1 → `VALIDATION_ERROR`
