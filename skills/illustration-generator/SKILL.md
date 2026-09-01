---
name: illustration-generator
description: Generate illustrations for each Visual Item based on the storyboard. Use for the image generation stage of the standard pipeline.
---

## 输入与输出

- 输入：Storyboard、风格/人物参考 Artifact、图片模型 profile；
- 输出：每个 Visual Item 的 source image、本地后处理 image 和 `illustrations.manifest`。

## 强制规则

- 图片模型不得生成中文、Logo 或水印；
- source 与本地后处理结果分开保存；
- 单图重生成只使该 `visual_id` 的 clip 和 final 失效；
- 素材必须通过 Artifact Store 读取；
- 不根据 `web|skill` 入口改变 prompt 或 Provider profile。

## CLI 命令

```bash
# 运行插画生成
python -m cli.csboard stage run --task <id> --run <run-id> --stage generate-illustrations --json

# 重试特定 Visual
python -m cli.csboard stage retry --task <id> --run <run-id> --stage generate-illustrations --visual visual-003-01 --json

# 查看插画清单
python -m cli.csboard artifact show --task <id> --run <run-id> --key illustrations.manifest --json
```

## 输出格式

成功时返回：

```json
{
  "ok": true,
  "command": "stage.run",
  "stage": "generate-illustrations",
  "result": "succeeded",
  "artifacts": ["illustrations.manifest"],
  "next_stage": "render-visuals"
}
```

## 与其他 Skill 的协作

- **上游**：storyboard-planner 生成 storyboard
- **下游**：visual-renderer 使用 illustrations 生成视频片段

## 错误处理

- storyboard 缺失 → 先运行 plan-storyboard
- 图片模型不可用 → `IMAGE_SERVICE_UNAVAILABLE`（可重试）
- 单图生成失败 → 可独立重试，不影响其他 Visual
