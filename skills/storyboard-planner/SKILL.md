---
name: storyboard-planner
description: Create visual storyboard from AV Plan and Timeline. Use for the visual planning stage of the standard pipeline.
---

## 输入与输出

- 输入：AV Plan、Timeline、style preset 或参考素材元数据、重点文字设置；
- 输出：`planning.storyboard`、全局视觉 bible和每个 Visual Item 的视觉规划。

## 强制规则

- 不改变 Unit/Visual 的原文、数量、顺序、范围或时间；
- 每个 Visual Item 对应一张主图，图片数量由 AV Plan 决定；
- 视觉一致性在全局 bible 中定义，不依赖上一张随机结果；
- 图片 prompt、overlay 和构图由共享 Prompt Builder 生成；
- WebUI 或 Skill 修改规划都必须通过共享 command 产生新 revision。

## CLI 命令

```bash
# 运行分镜规划
python -m cli.csboard stage run --task <id> --run <run-id> --stage plan-storyboard --json

# 查看生成的 Storyboard
python -m cli.csboard artifact show --task <id> --run <run-id> --key planning.storyboard --json
```

## 输出格式

成功时返回：

```json
{
  "ok": true,
  "command": "stage.run",
  "stage": "plan-storyboard",
  "result": "succeeded",
  "artifacts": ["planning.storyboard"],
  "next_stage": "generate-illustrations"
}
```

## 与其他 Skill 的协作

- **上游**：script-segmenter（av-plan）、voice-cloner（timeline）
- **下游**：illustration-generator 使用 storyboard 生成插画

## 错误处理

- av-plan 缺失 → 先运行 segment-script
- timeline 缺失 → 先运行 clone-voice
- 任务 pipeline 不是 mountain-av-v1 → `VALIDATION_ERROR`
