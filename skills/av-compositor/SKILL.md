---
name: av-compositor
description: Compose final video with audio, subtitles and quality validation. Use for the final composition stage of the standard pipeline.
---

## 输入与输出

- 输入：Voice Manifest、Timeline、Render Manifest、字幕与编码策略；
- 输出：可选 SRT、`output.final-video`、`output.final-manifest` 和 A/V 质量报告。

## 强制规则

- 字幕 cue 不跨 Voice Unit 边界；
- Voice 和 Visual 按稳定顺序恰好使用一次；
- 每个 Unit 的 Visual 完整覆盖对应 Voice 时长；
- 失败不得覆盖最后一个有效 final revision；
- `validation.passed != true` 时不能报告完成。

## CLI 命令

```bash
# 运行最终合成
python -m cli.csboard stage run --project <id> --run <run-id> --stage compose-video --json

# 查看最终清单
python -m cli.csboard artifact show --project <id> --run <run-id> --key output.final-manifest --json

# 导出诊断包
python -m cli.csboard diagnostics export --project <id> --run <run-id> --json
```

## 输出格式

成功时返回：

```json
{
  "ok": true,
  "command": "stage.run",
  "stage": "compose-video",
  "result": "succeeded",
  "artifacts": ["output.final-video", "output.final-manifest"],
  "validation": {"passed": true},
  "warnings": []
}
```

## 与其他 Skill 的协作

- **上游**：voice-cloner（voice-manifest、timeline）、visual-renderer（render-manifest）
- **下游**：无（最终阶段）

## 错误处理

- voice-manifest 缺失 → 先运行 clone-voice
- render-manifest 缺失 → 先运行 render-visuals
- A/V 时长不匹配 → `AV_DURATION_MISMATCH`
- 验证失败 → `VALIDATION_FAILED`（不报告完成）
- 编码失败 → `ENCODING_FAILED`（可重试）
