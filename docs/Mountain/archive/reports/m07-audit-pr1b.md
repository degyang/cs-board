# M07 PR-1b 审计：Provider Profile、SecretStore 与真实执行接线

## 概述

PR-1b 实现了 Provider Profile 系统和 SecretStore，将 `/api/v1` 端点与真实 Provider 配置连接起来，移除了硬编码的 `all_configured=False` 阻断。

## 关键变更

### 1. SecretStore 实现

**文件**: `csboard/adapters/secrets/secret_store.py`

安全存储敏感配置，不将 secret 写入 request.json、日志、诊断包或 API 响应。

```python
class SecretStore:
    def get(self, key: str) -> str | None
    def set(self, key: str, value: str) -> None
    def delete(self, key: str) -> bool
    def list_keys(self) -> list[str]
    def has(self, key: str) -> bool
```

**存储位置**: `{data_dir}/.secrets/secrets.json`
**文件权限**: 仅 owner 可读写（0600）

### 2. Provider Profile 系统

**文件**: `csboard/domain/provider_types.py`

定义了 6 种 Provider 类型：

| Provider | 类型 | 必需 Secret | 默认配置 |
|----------|------|-------------|----------|
| text_model | TEXT_MODEL | api_key | base_url, model, api_mode |
| image_model | IMAGE_MODEL | api_key | base_url, model |
| tts | TEXT_TO_SPEECH | 无 | url=http://127.0.0.1:7860, mode=gradio |
| alignment | ALIGNMENT | 无 | mode=node |
| renderer | RENDERER | 无 | 无 |
| media | MEDIA | 无 | 无 |

### 3. ProviderFactory

**文件**: `csboard/adapters/provider_factory.py`

根据 ProviderProfile 和 SecretStore 构造真实 Adapter 实例：

```python
class ProviderFactory:
    def check_provider(self, profile: ProviderProfile) -> dict[str, Any]
    def check_all_providers(self, profiles: dict[str, ProviderProfile]) -> dict[str, Any]
    def create_text_model(self, profile: ProviderProfile) -> TextModelPort
    def create_image_model(self, profile: ProviderProfile) -> ImageModelPort
    def create_tts(self, profile: ProviderProfile) -> TextToSpeechPort
    def create_alignment(self, profile: ProviderProfile) -> AlignmentPort
    def create_renderer(self, profile: ProviderProfile) -> RendererPort
    def create_media(self, profile: ProviderProfile) -> MediaPort
```

### 4. API 端点更新

**新增端点**:

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/providers` | GET | 列出所有 Provider 配置状态 |
| `/api/v1/providers/{name}/secrets` | POST | 设置 Provider secret |
| `/api/v1/providers/{name}/secrets` | GET | 获取 Provider secret 状态（掩码） |
| `/api/v1/providers/{name}/secrets/{key}` | DELETE | 删除 Provider secret |

**更新端点**:

- `/api/v1/capabilities` — 根据真实配置返回 supported 状态
- `/api/v1/health` — 读取真实 Provider 配置状态
- `/api/v1/projects/{id}/runs/{id}/start` — 检查真实 Provider 配置

### 5. Secret 安全性

**保证**:
- Secret 不写入 `request.json`
- Secret 不写入日志
- Secret 不写入诊断包
- Secret 不出现在 API 响应中（只返回掩码值）
- Secret 存储在 `.secrets/secrets.json`，权限 0600

**掩码示例**:
```
sk-1234567890abcdef → sk-1••••cdef
```

## 验收测试

### 测试用例 (25 个)

1. **test_v1_capabilities** — 能力列表返回
2. **test_v1_health** — 健康检查
3. **test_v1_list_providers** — Provider 列表
4. **test_v1_set_provider_secret** — 设置 secret
5. **test_v1_get_provider_secrets** — 获取 secret 状态
6. **test_v1_delete_provider_secret** — 删除 secret
7. **test_v1_project_lifecycle** — 项目生命周期
8. **test_v1_project_not_found** — 404 处理
9. **test_v1_upload_short_script** — 文案校验
10. **test_v1_upload_invalid_audio_format** — 音频格式校验
11. **test_v1_start_without_inputs** — 未上传时启动
12. **test_v1_cancel_run** — 取消运行
13. **test_v1_list_artifacts_empty** — 空产物列表
14. **test_v1_export_diagnostics** — 诊断包导出
15. **test_v1_project_detail_view** — 项目视图完整性
16. **test_v1_run_view** — Run 视图完整性
17. **test_v1_acceptance_flow_with_missing_provider** — **验收测试**
18. **test_v1_provider_configuration_enables_start** — 配置后启动
19. **test_v1_secret_not_in_response** — Secret 不回显
20. **test_v1_secret_not_in_health** — Secret 不在 health 中
21. **test_v1_no_legacy_references** — 无 legacy 依赖
22. **test_provider_factory_check_providers** — ProviderFactory 检查
23. **test_provider_factory_create_adapters** — ProviderFactory 构造 Adapter
24. **test_secret_store_basic_operations** — SecretStore 基本操作
25. **test_mask_secret** — 掩码函数

### 验收测试详情

```python
def test_v1_acceptance_flow_with_missing_provider(client, tmp_state):
    """创建项目 → 上传音频 → 启动真实标准流程 → 返回 CAPABILITY_NOT_AVAILABLE。"""

def test_v1_provider_configuration_enables_start(client, tmp_state):
    """配置所有 Provider 后，start 应该调用 MountainCommands.pipeline_run。"""

def test_v1_secret_not_in_response(client, tmp_state):
    """Secret 不应该出现在 API 响应中。"""
```

## 测试结果

```
pytest tests/ -v
============================= 244 passed, 5 skipped ==============================
```

## 遗留问题

1. **Pipeline 实际执行** — Provider 检查通过后，pipeline_run 内部可能需要更多依赖
2. **Adapter 初始化参数** — 部分 Adapter 需要额外配置（如 renderer_root）

## 结论

PR-1b 成功实现了 Provider Profile 系统和 SecretStore，将 `/api/v1` 端点与真实 Provider 配置连接起来。API 现在可以：

1. 读取真实 Provider 配置状态
2. 安全存储和管理 API Key
3. 在 Provider 未配置时返回 CAPABILITY_NOT_AVAILABLE
4. 在 Provider 配置完整时尝试启动 Pipeline

所有 244 个测试通过，无 legacy 依赖。
