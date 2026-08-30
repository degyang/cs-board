# M07 PR-1d: Provider API 契约测试纠偏与全量绿色门禁

## 目标

恢复全量绿色 Python 门禁。旧测试仍断言已淘汰的 ProviderFactory 参数签名、SecretStore 导出名和旧 API 文案/字段，按现行生产代码契约纠偏。

## 修改的测试与对应新契约

### 1. test_v1_list_providers
- **旧断言**: `provider["status"]["configured"]`（字段已淘汰）
- **新断言**: `provider["config_status"]` + `provider["availability"]`，验证结构字段：`configured`, `missing_secrets`, `configured_secrets`, `is_encrypted`, `available`, `component`

### 2. test_v1_acceptance_flow_with_missing_provider
- **旧断言**: `"Provider 未配置" in message`（过时文案）、`body["detail"]["missing"]`（已改名）
- **新断言**: `code == "CAPABILITY_NOT_AVAILABLE"`、`message` 非空（不绑定具体文案）、`body["detail"]["unavailable"]` 列表、`body["detail"]["details"]` 含 `provider` + `error_code`
- **新增**: monkeypatch `ProviderFactory.check_all_availability` 模拟不可用（真实 STATE_DIR 可能已有配置）

### 3. test_provider_factory_check_providers
- **旧调用**: `factory.check_all_providers(PROVIDER_PROFILES)`（旧签名，传 profile dict）
- **新调用**: `factory.check_all_providers()`（无参数，内部使用已加载 profiles）
- **断言**: `all_configured`, `providers`, `missing`, `configured` 字段

### 4. test_provider_factory_create_adapters
- **旧调用**: `factory.create_text_model(PROVIDER_PROFILES["text_model"])` 等（旧签名）
- **新调用**: `factory.create_text_model()` 等（无参数，内部从 profiles 获取）
- **保留**: "SecretStore 配置后能构造真实 Adapter" 行为验收

### 5. test_secret_store_basic_operations
- **旧导入**: `from csboard.adapters.secrets import SecretStore`（不存在）
- **新导入**: `from csboard.adapters.secrets import PlaintextSecretStore, mask_secret`
- **修正**: `store.delete()` 返回 `None`（非 `True`），增加 `mask_secret` 边界断言

### 新增: test_provider_dto_contract_no_deprecated_status_field
- 对 `/api/v1/providers`、`/health`、`/capabilities` 三个端点断言 Provider 字段不包含已淘汰的 `status` 字段
- 断言当前契约字段结构（`config_status`、`availability`）

## 门禁结果

| 门禁 | 结果 |
|---|---|
| `.venv/bin/python -m pytest -q` | **279 passed, 0 failed**, 5 skipped |
| `npm --prefix web-v2 run build` | ✅ tsc + vite build |
| `npm --prefix web-v2 test` | ✅ 107/107 passed |
| `git diff --check` | ✅ clean |

## 原则

- 不修改 Provider API 的当前真实行为
- 不回退 ProviderFactory、SecretStore 或 API DTO
- 不引入 fake provider、request.json API Key、localStorage Secret 或 legacy bridge
- 以当前生产代码为唯一契约
