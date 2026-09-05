# WEB-LOCAL-001 API 缺口记录

## 缺口: TTS 服务音频试听 API

**现状**: 当前 `POST /api/v1/services/{service_id}/probe` 仅探测服务连通性（返回 `ServiceAvailability`），不生成实际音频。

**需求**: 用户期望在本地服务页面点击"试听"后，能调用目标 TTS 服务生成一小段真实音频并播放，验证服务不仅能连通、还能正确合成语音。

**精确接口缺口**:

| 项目 | 说明 |
|------|------|
| 缺失端点 | `POST /api/v1/services/{service_id}/synthesize` |
| 请求体 | `{ "text": "试听文本", "voice_id"?: string, "format"?: "wav" \| "mp3" }` |
| 响应 | `audio/wav` 二进制流，或 `{ "audio_url": string, "content_type": string, "duration_ms": number }` |
| 权限 | 仅对 `capability ∈ {speech_synthesis, indextts}` 的服务有效 |
| 错误码 | `SERVICE_NOT_SPEECH` — 非语音合成服务; `SYNTHESIS_FAILED` — 合成失败; `MISSING_SECRET` — 缺少 API Key |

**替代方案评估**:

- `POST /api/v1/voice-profiles/{profile_id}/preview` — 已存在，但需要 `profile_id`（预置音色），不适用于任意本地 TTS 服务的连通性验证。
- `probeService()` — 只返回可用性布尔值和延迟，不生成音频。

**影响**: 当前页面"探测连通性"按钮调用 `probeService()` 验证服务是否在线，但无法验证语音合成是否实际可用。需要上述端点才能实现完整的"试听"功能。
