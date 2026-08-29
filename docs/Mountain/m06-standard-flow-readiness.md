# M06 标准流程真实性修复与验收准备

## 生产链路

标准白板流程只允许使用真实 Provider：

`segment-script → clone-voice → plan-storyboard → generate-illustrations → render-visuals → compose-video`

`Fake*` 适配器只能由测试显式注入，不能被 `MountainCommands` 的 Pipeline executor 使用。

## Project request 中的 Provider 配置

```json
{
  "script": "需要制作的视频文案。",
  "reference_audio": "/absolute/path/to/reference.wav",
  "tts_url": "http://127.0.0.1:7860",
  "tts_mode": "gradio",
  "whisper_mode": "node",
  "providers": {
    "text": {
      "base_url": "https://provider.example/v1",
      "model": "model-name",
      "api_key_env": "CSBOARD_TEXT_API_KEY"
    },
    "image": {
      "base_url": "https://provider.example/v1",
      "model": "image-model-name",
      "api_key_env": "CSBOARD_IMAGE_API_KEY"
    }
  }
}
```

密钥优先通过 `api_key_env` 提供；M07 Settings/API 将把它替换为 `secret_ref`。未配置 Provider 必须返回 `CAPABILITY_NOT_AVAILABLE`，不得回退到 Fake 或伪造成功。

## Artifact 契约

阶段消费者只能通过 Artifact Store logical key 定位输入：

| Key | 生产阶段 |
| --- | --- |
| `planning.av-plan` | segment-script |
| `audio.voice-manifest`、`timing.timeline` | clone-voice |
| `planning.storyboard` | plan-storyboard |
| `illustrations.manifest` | generate-illustrations |
| `render.manifest` | render-visuals |
| `output.final-video`、`output.final-manifest` | compose-video |

## 验收门槛

- Whisper character offsets 必须映射为 Visual source-range 边界；低置信度才允许整 Unit 等比例 fallback。
- Renderer 必须输出每个 Visual 的真实 MP4 clip，不得写占位文件。
- Composition 必须实际 concat 视频和音频、mux、烧录字幕，并通过 ffprobe 检查最终 MP4 的视频/音频流和时长。
- `tests/test_composition_service.py` 包含真实 FFmpeg 验收：生成短片、旁白、字幕，验证最终 MP4。
