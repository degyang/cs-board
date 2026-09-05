# Voice Provider Profile Backend 001

状态：完成，待集成验收；未提交。

## 范围

- 新增 provider-neutral `VoiceProfile` / `VoiceStyleProfile` 领域 DTO。
- 新增独立文件仓储 `settings/voice-profiles/`、`settings/voice-style-profiles/`，提供持久化 Profile。
- 新增 API：`GET/POST /api/v1/voice-profiles`、`GET/POST /api/v1/voice-style-profiles`，支持 `provider_id` 过滤。
- 注入 Mountain 唯一组合根；未修改 `web-v2`，未调用真实 MiMo，不接入动态信息图。

## 安全边界

- API Key 不读取、不复制到 profile DTO；Provider 是否已配置只通过 SecretStore 判定并返回布尔值。
- Profile 响应只包含 `provider_id`、模型、远程 Voice ID、设计描述、能力快照等非凭据字段。
- 非法或不完整的 Provider metadata 被忽略，不中断服务启动或列表 API。
- 创建时要求 Provider 存在、启用、具备 `speech_synthesis` 且 SecretStore 已配置；按 kind 校验远程 Voice ID 或设计提示词。
- 增加 `OpenAITTSAdapter`：兼容 `audio_generation` 历史 capability，解析逗号分隔模型列表，使用 SecretStore API Key 和 MiMo-compatible `audio: {format: "wav", voice: ...}` Chat Completions 请求；响应 base64 音频解码，错误统一脱敏。

## 验证

```text
python -m pytest -q tests/test_voice_profiles_api.py tests/test_capabilities_api.py tests/test_mountain_service_api.py tests/test_secret_security.py
专项新增测试及相关回归通过；已将旧的拒绝断言更新为正向 speech adapter 覆盖。

安全调用入口：`ProviderFactory.create_adapter(service_definition)` 返回 `OpenAITTSAdapter`，随后由 `TextToSpeechPort.synthesize(TTSRequest(...))` 调用；本轮仅通过 `unittest.mock.patch("httpx.post")` 验证 payload，未发起真实网络请求。
```

工作树仍包含其他已有修改；本工作包未执行提交、合并或推送。
