# PRESET-VOICE-UX-002-V — 预置音色创建契约独立复验回执

状态：**PASS**

独立复验确认 `PRESET-VOICE-UX-002-BE` 修复了 `PRESET-VOICE-UX-001-V` 中的真实创建契约缺口，并且现有预置音色 UX 门槛仍通过。未修改实现或规划，未重启 5182/8000，未执行 real render，未提交或推送。

## 独立验证证据

| 要求 | 独立证据 | 结论 |
| --- | --- | --- |
| UI-shaped create（无 `profile_id`） | 以 `TestClient(create_app(tempdir))` 创建启用、含凭据的 `speech_synthesis` 服务，POST `/api/v1/voice-profiles` 提交 `{name, kind: "provider-preset", provider_id, model_id, remote_voice_id, tags}`（无 `profile_id`）；返回 200 和 `preset-2f98f5602562c684091f7c9d287bc0838e900a2e667ee6afb52d1a30863cffba`。ID 为 `preset-` 加 64 位 hex，合法且稳定。 | PASS |
| 重复、重建及异身份不碰撞 | 对相同 provider/model/remote identity（仅改 name）重复 POST：200，响应与首次完全相同；用不同 model/remote identity POST：200、ID `preset-15a5932c16012ba0390006951cead4cf222b9b989c7ad90c884381d974a97504`，与首次不同；以相同临时数据目录重建 app 后读取，`total=2` 且两个 ID 均存在。 | PASS |
| MiMo 去重与 total | `tests/test_voice_profiles_api.py` 的非 mock API 覆盖通过：MiMo adapter/config 重复来源按规范化 `provider_id|model_id|remote_voice_id` 去重、重建稳定，别名目录 `total=8`，有两 model 的同 remote voice 保留为不同身份（总数 9）。实现的确定优先级为 stored override > configured metadata > adapter default。 | PASS |
| 无厂商/ID 硬编码、Provider 唯一数据源 | 审阅 `VoiceManagementPage.tsx`/`voiceProfiles.ts`：预置表单以 `fetchServices({ enabled: true })` 的结果过滤 `speech_synthesis`、`audio_generation`；渲染使用服务的 `service_id`/`display_name`，create DTO 不含厂商常量或 client `profile_id`。focused UI 测试验证 text-only 服务不进入选择器。 | PASS |
| 选中、独立试听、文本、preview、旧音频失效、错误态 | `voice-management.test.tsx` 覆盖并通过：卡片选择和编辑/保存、页面下方唯一 `独立试听区`、精确默认文本和自定义文本、`previewVoiceProfile(profileId, text)` 参数、生成中/失败状态，以及切换音色后 generation token 忽略旧响应并清除/暂停旧 audio。代码审阅亦确认 preview 区不在卡片或编辑表单中。 | PASS |

说明：预览成功链路的后端测试使用 adapter mock 验证真实应用 API/请求映射与受控音频结果；本验证没有外部 Provider 凭据，因此没有进行外部 real render/真实供应商请求，此项不在本工单允许范围内。

## 测试命令

| 命令 | 退出码 | 结果 | 耗时 |
| --- | ---: | --- | ---: |
| `pytest -q tests/test_voice_profiles_api.py` | 0 | 9 passed, 0 failed, 0 skipped | 6.70s（wall 6.89s） |
| `pytest -q tests/test_openai_tts_adapter.py tests/test_dynamic_provider_factory.py tests/test_mountain_api.py` | 0 | 25 passed, 0 failed, 0 skipped | 3.70s（wall 3.87s） |
| `cd web-v2 && npm test -- --run tests/voice-management.test.tsx tests/voice-profiles-api.test.ts` | 0 | 2 files, 14 passed, 0 failed, 0 skipped | 14.91s（wall 15.77s） |
| `cd web-v2 && npm test -- --reporter=dot` | 0 | 20 files, 444 passed, 0 failed, 0 skipped | 22.86s（wall 23.71s） |
| `cd web-v2 && npm run build` | 0 | TypeScript check + Vite production build passed | Vite 3.03s（wall 8.20s） |

仅有既有 Starlette `TestClient` 弃用警告、React Router future-flag 警告及无关 `act(...)` 测试警告；无失败或 skip。

## 出口

**PASS** — 可交 PM 对 `PRESET-VOICE-UX-001` 作最终接受决定。
