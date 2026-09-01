---
name: visual-renderer
description: Render video clips for each Visual Item using the whiteboard renderer. Use for the video rendering stage of the standard pipeline.
---

## 输入与输出

- 输入：Illustration Manifest、Timeline、renderer 设置和可选 annotation revision；
- 输出：每个 Visual Item 的 clip、silent master 和 `render.manifest`。

## 强制规则

- `engine=whiteboard` 使用白板 renderer，`engine=infographic-remotion` 使用 Remotion adapter；
- 每个 clip 的目标时长只取 Timeline，不重复运行 Whisper 或计算 fallback；
- 校验开场无提前露图、最终帧完整、尺寸/fps 和时长容差；
- annotation 修改只重绘受影响 Visual；
- 不执行最终音画合成。

## CLI 命令

```bash
# 运行视觉渲染
python -m cli.csboard stage run --task <id> --run <run-id> --stage render-visuals --json

# 重试特定 Visual
python -m cli.csboard stage retry --task <id> --run <run-id> --stage render-visuals --visual visual-003-01 --json

# 查看渲染清单
python -m cli.csboard artifact show --task <id> --run <run-id> --key render.manifest --json
```

## 输出格式

成功时返回：

```json
{
  "ok": true,
  "command": "stage.run",
  "stage": "render-visuals",
  "result": "succeeded",
  "artifacts": ["render.manifest"],
  "next_stage": "compose-video"
}
```

## 与其他 Skill 的协作

- **上游**：illustration-generator（illustrations）、voice-cloner（timeline）
- **下游**：av-compositor 使用 render-manifest 合成最终视频

## 错误处理

- illustrations 缺失 → 先运行 generate-illustrations
- timeline 缺失 → 先运行 clone-voice
- renderer 不可用 → `RENDERER_UNAVAILABLE`（可重试）
- 单个 Visual 渲染失败 → 可独立重试
