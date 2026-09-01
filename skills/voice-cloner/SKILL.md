---
name: voice-cloner
description: Generate unit-level voice synthesis with Whisper alignment and fallback timing. Use for the voice production stage of the standard pipeline.
---

## 输入与输出

- 输入：AV Plan、参考音频、TTS profile 和 Whisper profile；
- 输出：每个 Voice Unit 的规范化 WAV、`audio.voice-manifest`、`timing.timeline`、兼容母带和质量告警。

## 强制规则

- 每个 Voice Unit 独立生成一条 Voice；默认顺序合成，验证音色一致性后才允许小并发；
- 有效单元音频不得重复调用 TTS，失败单元可单独重试；
- TTS 输入严格等于 Unit 原文，临时写入、probe 后原子提交；
- 每条 Voice 尝试 Whisper 对齐，并验证覆盖率、单调性和边界；
- 对齐无效时整个 Unit 使用实际 Voice 时长按 Visual Item 数量等分；
- 必须登记 `timing_source=whisper|equal_fallback` 和稳定 reason code；
- fallback 产生 warning 和事件，但不使任务失败。

## CLI 命令

```bash
# 运行语音克隆
python -m cli.csboard stage run --task <id> --run <run-id> --stage clone-voice --reference /path/to/reference.wav --json

# 重试特定 Unit
python -m cli.csboard stage retry --task <id> --run <run-id> --stage clone-voice --unit unit-003 --json

# 使用自定义 TTS 服务
python -m cli.csboard stage run --task <id> --run <run-id> --stage clone-voice --reference ref.wav --tts-url http://localhost:8080 --tts-mode fastapi --json
```

## 输出格式

成功时返回：

```json
{
  "ok": true,
  "command": "stage.run",
  "stage": "clone-voice",
  "result": "succeeded",
  "artifacts": ["audio.voice-manifest", "timing.timeline"],
  "warnings": [],
  "next_stage": "plan-storyboard"
}
```

## 与其他 Skill 的协作

- **上游**：script-segmenter 生成 av-plan
- **下游**：storyboard-planner 使用 timeline，av-compositor 使用 voice-manifest

## 错误处理

- av-plan 缺失 → 先运行 generate-visual-anchors
- TTS 服务不可用 → `TTS_SERVICE_UNAVAILABLE`（可重试）
- Whisper 对齐失败 → 使用等分 fallback + warning
- 参考音频缺失 → `VALIDATION_ERROR`
