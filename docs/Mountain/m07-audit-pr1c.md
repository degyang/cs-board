# M07 PR-1c: ProviderFactory → MountainCommands 真实执行接线 审计报告

## 验收状态: ✅ 通过

所有 19 项验收测试全部通过。

## 完成的变更

### 1. ProviderFactory 成为唯一 Provider 构造入口

**文件**: `csboard/application/commands.py`

- MountainCommands 接受 ProviderFactory 作为依赖注入
- `__post_init__` 自动创建 ProviderFactory 实例（如未提供）
- 六阶段执行器全部使用 ProviderFactory 构造真实 Adapter：
  - `_exec_clone_voice` → `factory.create_tts()`
  - `_exec_plan_storyboard` → `factory.create_text_model()`
  - `_exec_generate_illustrations` → `factory.create_image_model()`
  - `_exec_render_visuals` → `factory.create_alignment()` + `factory.create_renderer()`
  - `_exec_compose_video` → `factory.create_media()`

### 2. 禁止从 request.json 读取 API Key

**已删除方法**:
- `_provider_config()` — 旧实现从 request.json 读取 providers 配置
- `_text_model_from_request()` — 旧实现从 request.json 构造 TextModel
- `_image_model_from_request()` — 旧实现从 request.json 构造 ImageModel

### 3. request.json 只保存非敏感参数

**文件**: `webapp/mountain_v1_api.py`

上传端点 `/api/v1/projects/{project_id}/inputs` 保存的字段:
- `script` — 剧本文本
- `reference_audio` — 参考音频路径
- `style` — 视觉风格
- `include_subtitles` — 是否包含字幕
- `pen_text` — 画笔文本
- `stroke_detail` — 笔画细节

**不包含任何 API Key 或敏感信息**。

### 4. API Key 通过 SecretStore 读取

**文件**: `csboard/adapters/provider_factory.py`

- `ProviderFactory.__init__` 使用 `create_secret_store(data_dir, encrypted)` 创建 SecretStore
- `_get_secrets(profile)` 从 SecretStore 读取 secret
- `create_text_model()` 和 `create_image_model()` 通过 SecretStore 获取 api_key

### 5. Pipeline 六阶段使用 ProviderFactory 构造的真实 Adapter

**验收测试**: `test_pipeline_stages_use_provider_factory`

验证 `_run_stage` 方法调用:
```python
factory.create_tts()
factory.create_text_model()
factory.create_image_model()
factory.create_alignment()
factory.create_renderer()
factory.create_media()
```

### 6. health 和 capabilities 实际检查可用性

**文件**: `webapp/mountain_v1_api.py`

- `/api/v1/health` 调用 `provider_factory.check_all_providers()`
- `/api/v1/capabilities` 调用 `provider_factory.check_all_providers()`
- 返回 `all_configured`、`configured`、`missing` 列表

**ProviderFactory.check_all_providers()** 检查每个 Provider 的 secret 是否已配置。

### 7. start 行为正确处理

**文件**: `webapp/mountain_v1_api.py`

- 未配置 Provider 时返回 `CAPABILITY_NOT_AVAILABLE`（HTTP 400）
- 已配置 Provider 时调用 `pipeline_run()` 实际执行

### 8. SecretStore 支持 Fernet 加密

**文件**: `csboard/adapters/secrets/secret_store.py`

- `create_secret_store(data_dir, encrypted=True)` 优先使用 Fernet 加密
- 当 `cryptography` 不可用时自动降级到明文存储
- `CSBOARD_MASTER_KEY` 环境变量控制加密密钥

### 9. Provider Profile 配置持久化

**文件**: `csboard/adapters/provider_factory.py`

- `update_profile_config(name, config)` 保存非敏感配置到 `.profiles/` 目录
- 配置文件不包含 API Key
- 配置在重启后持久化

## 关键设计决策

### 1. MountainCommands 创建项目时自动创建 Run

为兼容现有的 `get_project` API 返回 `active_run` 的行为，`create_project` 现在：
- 同时创建 `project.json` 和 `run.json`
- 设置 `active_run_id` 指向新创建的 Run
- Run 使用 domain 模型兼容的格式（trace_id, entrypoint, command_ids 等）

### 2. ProviderFactory 在路由创建时初始化

`mountain_v1_router()` 在创建路由时初始化 ProviderFactory，确保：
- 所有端点共享同一个 ProviderFactory 实例
- SecretStore 配置在端点间一致

### 3. 事件系统简化

新增 `csboard/application/events.py`:
- `EventEmitter` 抽象基类
- `NoopEmitter` 空操作实现
- 供 MountainCommands 使用

## 测试覆盖

### 19 项验收测试

| # | 测试 | 验收标准 |
|---|------|----------|
| 1 | `test_provider_factory_is_sole_entry` | ProviderFactory 是唯一入口 |
| 2 | `test_mountain_commands_uses_provider_factory` | MountainCommands 使用 ProviderFactory |
| 3 | `test_request_json_no_api_key` | request.json 不保存 API Key |
| 4 | `test_api_key_via_secret_store` | API Key 通过 SecretStore 读取 |
| 5 | `test_api_key_not_in_request_json_after_upload` | 上传后无 API Key |
| 6 | `test_pipeline_stages_use_provider_factory` | 六阶段使用 ProviderFactory |
| 7 | `test_stage_executors_receive_adapter` | 执行器接收真实 Adapter |
| 8 | `test_health_checks_availability` | health 检查可用性 |
| 9 | `test_capabilities_checks_availability` | capabilities 检查可用性 |
| 10 | `test_health_with_configured_providers` | 配置后 health 返回 ok |
| 11 | `test_start_returns_capability_not_available_when_missing` | 未配置返回 CAPABILITY_NOT_AVAILABLE |
| 12 | `test_start_runs_pipeline_when_configured` | 已配置实际运行 pipeline |
| 13 | `test_secret_store_encrypted_by_default` | SecretStore 默认加密 |
| 14 | `test_secret_store_falls_back_to_plaintext` | 无 cryptography 时降级 |
| 15 | `test_provider_config_persists` | 配置持久化 |
| 16 | `test_provider_config_does_not_store_secrets` | 配置不存储 secret |
| 17 | `test_full_flow_with_provider_factory` | 完整流程验收 |
| 18 | `test_provider_factory_constructs_real_adapters` | 构造真实 Adapter |
| 19 | `test_no_global_singleton_dependency` | 无全局单例依赖 |

## 文件变更清单

| 文件 | 变更类型 |
|------|----------|
| `csboard/application/commands.py` | 重构：使用 ProviderFactory，删除旧 _provider_config |
| `csboard/application/events.py` | 新增：事件系统接口 |
| `csboard/adapters/provider_factory.py` | 重构：支持 create_secret_store |
| `csboard/adapters/secrets/secret_store.py` | 新增：create_secret_store 工厂函数 |
| `csboard/domain/errors.py` | 新增：StageFailedError |
| `webapp/mountain_v1_api.py` | 修复：传入 ProviderFactory，修复 API 调用 |
| `tests/test_m07_pr1c_acceptance.py` | 新增：19 项验收测试 |
| `docs/Mountain/m07-audit-pr1c.md` | 新增：审计报告 |
