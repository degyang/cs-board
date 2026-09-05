# PRESET-VOICE-UX-001-BE — Voice Profiles 身份、去重与真实试听契约

## 完成范围

| 文件 | 变更 |
| --- | --- |
| `csboard/application/voice_profiles.py` | 为 provider preset 定义 `service_id | model_id | remote_voice_id` 的 NFKC、trim、casefold 稳定身份键；按 stored override > 服务配置元数据 > adapter 默认值的固定优先级及稳定次序去重；目录响应在去重后计算。preview 仅使用 profile 指向且服务已声明的模型和远端 voice，Provider 调用前删除旧受控 artifact，失败不会留下旧音频。 |
| `webapp/mountain_voice_profile_api.py` | 增加最小 `PATCH /api/v1/voice-profiles/{profile_id}`，用于把对 adapter 预置音色的编辑保存为本地 override；不接受 provider 身份改写。 |
| `tests/test_voice_profiles_api.py` | 覆盖 MiMo 重复来源、跨重建身份/顺序稳定、同名不同模型保留、`total` 一致、真实 preview 的 voice/format 参数、Provider secret 错误安全化且无残留 artifact，以及预置 profile 编辑保存。 |

未修改 `docs/Mountain/`、`web-v2`、旧 webapp 路径或无关服务；未重启 5182/8000，未提交或推送。

## 命令与结果

| 命令 | 退出码 | 通过/失败/跳过 | 耗时 |
| --- | --- | --- | --- |
| `pytest -q tests/test_voice_profiles_api.py` | 0 | 8 / 0 / 0 | 5.12s |
| `pytest -q tests/test_openai_tts_adapter.py tests/test_dynamic_provider_factory.py tests/test_mountain_api.py` | 0 | 25 / 0 / 0 | 1.78s |

两组均只有现有 Starlette/httpx deprecation warning，无 skip。

## 未覆盖风险

未调用外部真实 Provider；定向测试以 adapter mock 验证请求映射和安全错误契约。实际网络、凭据和远端音频编码仍由部署环境验证。
