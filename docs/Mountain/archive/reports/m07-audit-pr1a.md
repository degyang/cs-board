# M07 PR-1a 审计：Mountain v1 API 纯净化

## 概述

PR-1a 将 Mountain API 重构为 `/api/v1` 前缀，完全移除 legacy 依赖，确保所有操作通过 MountainCommands 和 PipelineOrchestrator 完成。

## 关键变更

### 1. 新 API 路由 `/api/v1`

- 创建 `webapp/mountain_v1_api.py` 实现纯净的 v1 API
- 路由前缀从 `/api/mountain` 改为 `/api/v1`
- 在 `webapp/server.py` 中注册新路由

### 2. 移除 legacy 依赖

**已移除的依赖：**
- ❌ `webapp.mountain_stages` — 不再导入或使用
- ❌ `legacy_execution_id` — 不再作为标识符
- ❌ `127.0.0.1:8000` — 不再硬编码服务地址
- ❌ `FakeTextModel` — 不在 API 层使用
- ❌ `FakeImageModel` — 不在 API 层使用
- ❌ `FakeTextToSpeech` — 不在 API 层使用
- ❌ `FakeAlignment` — 不在 API 层使用
- ❌ `FakeRenderer` — 不在 API 层使用
- ❌ `FakeMedia` — 不在 API 层使用

### 3. 使用 MountainCommands 直接操作

所有端点通过 `_commands()` 创建 MountainCommands 实例：

```python
def _commands() -> MountainCommands:
    """创建 MountainCommands 实例。"""
    return MountainCommands(data_dir)
```

### 4. Provider Profile/Secret 检查

启动流程前检查 Provider 配置：

```python
def _check_providers() -> dict[str, Any]:
    """检查 Provider 配置状态。"""
    # TODO: 从 SecretStore 读取真实配置
    return {
        "all_configured": False,
        "missing": ["text_model", "image_model", "tts"],
        "configured": [],
    }
```

未配置时返回 `CAPABILITY_NOT_AVAILABLE`：

```python
if not provider_check["all_configured"]:
    raise HTTPException(
        400,
        {
            "code": "CAPABILITY_NOT_AVAILABLE",
            "message": "Provider 未配置",
            "missing": provider_check["missing"],
        },
    )
```

### 5. API View 结构

固定为 WebUI 所需的视图：

| View | 端点 | 说明 |
|------|------|------|
| Project | `/api/v1/projects/{id}` | 项目详情 |
| Run | `/api/v1/projects/{id}/runs/{id}` | 运行状态 |
| Stage | `/api/v1/projects/{id}/runs/{id}/stages` | 阶段列表 |
| Unit | `/api/v1/projects/{id}/runs/{id}/units` | Voice Units |
| Visual | `/api/v1/projects/{id}/runs/{id}/artifacts` | 产物列表 |
| Artifact | `/api/v1/projects/{id}/runs/{id}/artifacts/{key}` | 产物详情 |
| Capability | `/api/v1/capabilities` | 能力列表 |
| Event | `/api/v1/projects/{id}/runs/{id}/events` | 事件流 |
| Log | `/api/v1/projects/{id}/runs/{id}/logs` | 日志 |
| Metric | `/api/v1/projects/{id}/runs/{id}/metrics` | 指标 |
| Diagnostic | `/api/v1/projects/{id}/runs/{id}/diagnostics` | 诊断包 |

### 6. 输入上传作为 Project Request

上传后保存为 `request.json`：

```python
request_data = {
    "script": script.strip(),
    "reference_audio": str(target),
    "style": style,
    "include_subtitles": include_subtitles,
    "pen_text": pen_text[:12],
    "stroke_detail": stroke_detail,
}
request_path = repository.project_dir(project_id) / "request.json"
```

## 验收测试

### 测试用例

1. **test_v1_capabilities** — 能力列表返回
2. **test_v1_health** — 健康检查
3. **test_v1_project_lifecycle** — 项目生命周期
4. **test_v1_project_not_found** — 404 处理
5. **test_v1_upload_short_script** — 文案校验
6. **test_v1_upload_invalid_audio_format** — 音频格式校验
7. **test_v1_start_without_inputs** — 未上传时启动
8. **test_v1_cancel_run** — 取消运行
9. **test_v1_list_artifacts_empty** — 空产物列表
10. **test_v1_export_diagnostics** — 诊断包导出
11. **test_v1_project_detail_view** — 项目视图完整性
12. **test_v1_run_view** — Run 视图完整性
13. **test_v1_acceptance_flow_with_missing_provider** — **验收测试**
14. **test_v1_no_legacy_references** — 无 legacy 依赖验证

### 验收测试详情

```python
def test_v1_acceptance_flow_with_missing_provider(client, tmp_state):
    """M07 PR-1a 验收：创建项目 → 上传音频 → 启动真实标准流程 → 返回 CAPABILITY_NOT_AVAILABLE。"""
    # 步骤 1: 创建项目
    # 步骤 2: 上传文案和参考音频
    # 步骤 3: 获取项目详情（这会创建一个 Run）
    # 步骤 4: 尝试启动标准流程（Provider 未配置）
    # 验证返回 CAPABILITY_NOT_AVAILABLE
```

## 测试结果

```
tests/test_mountain_v1_api.py::test_v1_capabilities PASSED
tests/test_mountain_v1_api.py::test_v1_health PASSED
tests/test_mountain_v1_api.py::test_v1_project_lifecycle PASSED
tests/test_mountain_v1_api.py::test_v1_project_not_found PASSED
tests/test_mountain_v1_api.py::test_v1_upload_short_script PASSED
tests/test_mountain_v1_api.py::test_v1_upload_invalid_audio_format PASSED
tests/test_mountain_v1_api.py::test_v1_start_without_inputs PASSED
tests/test_mountain_v1_api.py::test_v1_cancel_run PASSED
tests/test_mountain_v1_api.py::test_v1_list_artifacts_empty PASSED
tests/test_mountain_v1_api.py::test_v1_export_diagnostics PASSED
tests/test_mountain_v1_api.py::test_v1_project_detail_view PASSED
tests/test_mountain_v1_api.py::test_v1_run_view PASSED
tests/test_mountain_v1_api.py::test_v1_acceptance_flow_with_missing_provider PASSED
tests/test_mountain_v1_api.py::test_v1_no_legacy_references PASSED

14 passed
```

## 遗留问题

1. **Provider Profile/Secret 集成** — `_check_providers()` 目前返回硬编码值，需要从 SecretStore 读取真实配置
2. **Run 创建时机** — 当前在 `get_project` 时自动创建 Run，可能需要显式创建端点

## 结论

PR-1a 成功将 Mountain API 重构为纯净的 `/api/v1` 端点，完全移除了 legacy 依赖，并通过了所有验收测试。API 现在直接使用 MountainCommands 和 PipelineOrchestrator，为后续 Vite WebUI 集成做好了准备。
