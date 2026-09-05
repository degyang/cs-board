# PRESET-VOICE-UX-001-BE — Voice Profiles 身份、去重与真实试听契约

`worker_backend`，请只完成后端范围；可与前端工单并行。

工作目录：`/mnt/d/Workstation/Projects/cs-board`

回执写入：`docs/workmates/receipts/PRESET-VOICE-UX-001-BE.md`

范围：`csboard/application/voice_profiles.py`、相关 domain/port/adapter 文件、`webapp/mountain_voice_profile_api.py`，以及直接相关的 `tests/test_voice_profiles_api.py`。如 API 契约需要最小补充，可改相邻的 native API composition；不得改 `web-v2`、动态信息图规划、旧 webapp 路径或无关服务。

交付要求：

1. 修复 `voice-profiles` 当前 MiMo 音色重复。为 Provider 预置音色定义稳定身份：使用 Provider/service 身份、模型身份和远端音色身份的规范化复合键；不得以展示名称、数组位置或厂商硬编码作为身份。
2. 在目录聚合/返回前按该稳定键去重；相同身份仅返回一条，分页 `items` / `total` 一致且重复来源的选择有确定规则。不同 provider、model 或 remote voice identity 的同名音色不得被误合并。
3. 保持/补齐 preview endpoint 的真实 Provider 调用链：profile → 已声明的 provider/model/remote voice → provider adapter preview/TTS → 返回受控 `audio_url`、content type、duration（如可得）。配置/Provider 失败必须返回安全错误，绝不返回伪造音频或泄露 secret/raw provider body。
4. 增加后端测试，覆盖 MiMo 重复重建后的去重、稳定身份跨请求一致、同名但不同身份保留、response total、一条 profile 的真实 adapter 参数映射，以及 provider failure 的安全错误/无 preview artifact。

门槛：运行 focused `tests/test_voice_profiles_api.py`（以及新增直接测试）和适当的后端全量/受影响 suite；回执列命令、退出码、通过/失败/skip 数、耗时及未覆盖风险。无需且不得为本工单重启 5182/8000。不得自行验收、不得提交或推送。
