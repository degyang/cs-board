# PRESET-VOICE-UX-002-BE — 后端创建契约修复回执

状态：**READY_FOR_INDEPENDENT_VERIFICATION**

## 已完成

- `provider-preset` 创建请求未提供 `profile_id` 时，后端使用规范化的 `provider_id | model_id | remote_voice_id`（NFKC、trim、casefold）计算 SHA-256，并返回 `preset-<64 hex>` 的合法、稳定本地 ID；前端无需猜测或硬编码厂商/ID。
- 同一规范化预置身份的重复 POST 现在是幂等的：返回已有的确定性 profile（包括由服务元数据或 adapter 默认项投影出的条目），不创建第二条记录。
- 不同 provider、model 或 remote voice identity 参与 ID 输入，因而生成不同的稳定 ID。
- 在 `tests/test_voice_profiles_api.py` 添加了非 mock、in-process HTTP API 回归：直接 POST 与 UI 相同的无 `profile_id` body；断言成功、稳定 ID、重复提交、重建读取，以及同名但 model/remote voice/provider 身份不同的非碰撞结果。

## 测试证据

| 命令 | 退出码 | 通过 | 失败 | Skip | 耗时 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `pytest -q tests/test_voice_profiles_api.py` | 0 | 9 | 0 | 0 | 2.82s（wall 3.05s） |
| `pytest -q tests/test_openai_tts_adapter.py tests/test_dynamic_provider_factory.py tests/test_mountain_api.py` | 0 | 25 | 0 | 0 | 1.65s（wall 1.86s） |

两组测试均仅出现既有 Starlette `TestClient` 弃用警告；没有失败或 skip。

## 边界确认

- 仅修改 `csboard/application/voice_profiles.py`、`tests/test_voice_profiles_api.py` 与本回执；无需改动 native API router。
- 未修改 `web-v2`、动态信息图规划或无关路径；未重启 5182/8000，未提交、未推送，未执行 real render。

请由独立验证角色复核，不在本回执中自行验收。
