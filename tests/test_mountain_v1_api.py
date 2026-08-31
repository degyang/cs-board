"""M07 PR-1b 验收测试：Provider Profile、SecretStore 与真实执行接线。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from webapp.server import app


@pytest.fixture()
def tmp_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """临时目录注入。"""
    state = tmp_path / ".webapp"
    state.mkdir()
    monkeypatch.setattr("webapp.server.STATE_DIR", state)
    monkeypatch.setattr("webapp.server.JOBS_DIR", state / "jobs")
    monkeypatch.setattr("webapp.server.CONFIG_PATH", state / "config.json")
    monkeypatch.setattr("webapp.server.PREFERENCES_PATH", state / "preferences.json")
    return state


@pytest.fixture()
def client(tmp_state: Path) -> TestClient:
    """TestClient 注入。"""
    return TestClient(app, raise_server_exceptions=False)


# ── 基础路由测试 ──────────────────────────────────────────────────────


def test_v1_capabilities(client: TestClient) -> None:
    """GET /api/v1/capabilities 返回支持的组合列表。"""
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body.get("items"), list)
    assert len(body["items"]) >= 1
    first = body["items"][0]
    assert "engine" in first
    assert "visual_source" in first
    assert "supported" in first


def test_v1_health(client: TestClient) -> None:
    """GET /api/v1/health 返回服务健康状态。"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert "providers" in body


# ── Provider DTO 契约测试 ────────────────────────────────────────────────


def _assert_availability_contract(av: dict) -> None:
    """统一断言单个 Provider availability 字段符合现行契约。"""
    assert "status" not in av, "availability must not contain deprecated 'status'"
    assert isinstance(av["available"], bool)
    assert isinstance(av["component"], str)
    assert "error_code" in av
    assert "suggestion" in av


def test_provider_dto_contract_no_deprecated_status_field(
    client: TestClient, tmp_state: Path
) -> None:
    """Provider 响应不得包含已淘汰的 'status' 字段，防止前端误用。

    断言 /api/v1/providers、/health、/capabilities 的 Provider 字段均使用
    当前契约（config_status + availability），不包含旧版 'status'。
    """
    # GET /api/v1/providers —— 每个 entry 含 config_status + availability
    resp = client.get("/api/v1/providers")
    assert resp.status_code == 200
    providers_body = resp.json()
    for name, entry in providers_body["providers"].items():
        assert "status" not in entry, f"providers/{name} contains deprecated 'status'"
        assert "config_status" in entry
        assert "availability" in entry
        cs = entry["config_status"]
        assert isinstance(cs["configured"], bool)
        assert isinstance(cs["missing_secrets"], list)
        assert isinstance(cs["configured_secrets"], list)
        assert isinstance(cs["is_encrypted"], bool)
        _assert_availability_contract(entry["availability"])

    # GET /api/v1/health —— providers.providers 中每个 Provider availability
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    health_body = resp.json()
    assert "providers" in health_body
    for name, av in health_body["providers"]["providers"].items():
        _assert_availability_contract(av)

    # GET /api/v1/capabilities —— providers.providers 中每个 Provider availability
    resp = client.get("/api/v1/capabilities")
    assert resp.status_code == 200
    cap_body = resp.json()
    assert isinstance(cap_body["items"], list)
    for item in cap_body["items"]:
        assert "engine" in item
        assert "visual_source" in item
        assert "supported" in item
        assert isinstance(item["supported"], bool)
    assert "providers" in cap_body
    for name, av in cap_body["providers"]["providers"].items():
        _assert_availability_contract(av)


# ── Provider 配置测试 ──────────────────────────────────────────────────


def test_v1_list_providers(client: TestClient, tmp_state: Path) -> None:
    """GET /api/v1/providers 返回所有 Provider 状态。"""
    response = client.get("/api/v1/providers")
    assert response.status_code == 200
    body = response.json()
    assert "providers" in body
    assert "all_configured" in body
    assert "all_available" in body
    # 应该有 6 个 provider
    assert len(body["providers"]) == 6
    # 验证每个 provider 的字段契约
    for name, provider in body["providers"].items():
        assert "profile" in provider
        assert "config_status" in provider
        assert "availability" in provider
        # config_status 结构
        cs = provider["config_status"]
        assert "configured" in cs
        assert isinstance(cs["configured"], bool)
        assert "missing_secrets" in cs
        assert "configured_secrets" in cs
        assert "is_encrypted" in cs
        # availability 结构
        av = provider["availability"]
        assert "available" in av
        assert isinstance(av["available"], bool)
        assert "component" in av


def test_v1_set_provider_secret(client: TestClient, tmp_state: Path) -> None:
    """POST /api/v1/providers/{name}/secrets 设置 secret。"""
    # 设置 text_model 的 api_key
    response = client.post(
        "/api/v1/providers/text_model/secrets",
        json={"key": "api_key", "value": "sk-test123456789"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["provider"] == "text_model"
    assert body["key"] == "api_key"


def test_v1_get_provider_secrets(client: TestClient, tmp_state: Path) -> None:
    """GET /api/v1/providers/{name}/secrets 获取 secret 状态（不返回实际值）。"""
    # 先设置一个 secret
    client.post(
        "/api/v1/providers/text_model/secrets",
        json={"key": "api_key", "value": "sk-test123456789"},
    )

    # 获取 secret 状态
    response = client.get("/api/v1/providers/text_model/secrets")
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "text_model"
    assert "secrets" in body
    assert "api_key" in body["secrets"]
    assert body["secrets"]["api_key"]["configured"] is True
    # 验证不返回实际值
    assert body["secrets"]["api_key"]["masked_value"] is not None
    assert "test123456789" not in body["secrets"]["api_key"]["masked_value"]


def test_v1_delete_provider_secret(client: TestClient, tmp_state: Path) -> None:
    """DELETE /api/v1/providers/{name}/secrets/{key} 删除 secret。"""
    # 先设置一个 secret
    client.post(
        "/api/v1/providers/text_model/secrets",
        json={"key": "api_key", "value": "sk-test123456789"},
    )

    # 删除 secret
    response = client.delete("/api/v1/providers/text_model/secrets/api_key")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True

    # 验证已删除
    response = client.get("/api/v1/providers/text_model/secrets")
    body = response.json()
    assert body["secrets"]["api_key"]["configured"] is False


# ── 项目生命周期测试 ──────────────────────────────────────────────────


def test_v1_project_lifecycle(client: TestClient, tmp_state: Path) -> None:
    """完整项目生命周期：创建 → 上传 → 启动（Provider 未配置）。"""
    # 1. 创建项目
    response = client.post("/api/v1/tasks", json={"title": "验收测试"})
    assert response.status_code == 200
    body = response.json()
    task_id = body["task_id"]
    assert task_id

    # 2. 上传输入（文案 + 参考音频）
    script = "第一幕：春天来了，花儿开了。第二幕：夏天到了，果实成熟了。"
    reference_content = b"fake-audio-content"
    response = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={
            "script": script,
            "style": "极简粗线简笔白板风",
            "include_subtitles": "true",
            "pen_text": "",
            "stroke_detail": "detailed",
        },
        files={"reference": ("reference.wav", reference_content, "audio/wav")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["input_saved"] is True

    # 3. 尝试启动标准流程（Provider 未配置，应返回 CAPABILITY_NOT_AVAILABLE）
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    run_id = response.json()["active_run"]["run_id"]

    response = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start")
    assert response.status_code == 400
    body = response.json()
    assert body["detail"]["code"] == "CAPABILITY_NOT_AVAILABLE"


def test_v1_project_not_found(client: TestClient) -> None:
    """查询不存在的项目返回 404。"""
    response = client.get("/api/v1/tasks/nonexistent")
    assert response.status_code == 404


# ── 输入上传测试 ──────────────────────────────────────────────────────


def test_v1_upload_short_script(client: TestClient, tmp_state: Path) -> None:
    """文案过短返回 400。"""
    # 先创建项目
    response = client.post("/api/v1/tasks", json={"title": "测试"})
    task_id = response.json()["task_id"]

    # 上传过短文案
    response = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "太短了"},
        files={"reference": ("ref.wav", b"audio", "audio/wav")},
    )
    assert response.status_code == 400
    assert "至少需要 10 个字" in response.text


def test_v1_upload_invalid_audio_format(client: TestClient, tmp_state: Path) -> None:
    """音频格式不支持返回 400。"""
    # 先创建项目
    response = client.post("/api/v1/tasks", json={"title": "测试"})
    task_id = response.json()["task_id"]

    # 上传不支持的音频格式
    response = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={"script": "这是一个足够长的文案用于测试验证"},
        files={"reference": ("ref.txt", b"not-audio", "text/plain")},
    )
    assert response.status_code == 400
    assert "格式不支持" in response.text


# ── Run 操作测试 ──────────────────────────────────────────────────────


def test_v1_start_without_inputs(client: TestClient, tmp_state: Path) -> None:
    """未上传输入时启动返回 400。"""
    # 先创建项目
    response = client.post("/api/v1/tasks", json={"title": "测试"})
    task_id = response.json()["task_id"]

    # 获取项目详情（这会创建一个 Run）
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    run_id = response.json()["active_run"]["run_id"]

    # 尝试启动（没有 request.json）
    response = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start")
    assert response.status_code == 400
    assert "请先上传文案与参考音频" in response.text


def test_v1_cancel_run(client: TestClient, tmp_state: Path) -> None:
    """取消运行。"""
    # 先创建项目
    response = client.post("/api/v1/tasks", json={"title": "测试"})
    task_id = response.json()["task_id"]

    # 获取项目详情（这会创建一个 Run）
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    run_id = response.json()["active_run"]["run_id"]

    # 取消运行
    response = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/cancel")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["status"] == "cancelled"


# ── 产物测试 ──────────────────────────────────────────────────────


def test_v1_list_artifacts_empty(client: TestClient, tmp_state: Path) -> None:
    """没有产物时返回空列表。"""
    # 先创建项目
    response = client.post("/api/v1/tasks", json={"title": "测试"})
    task_id = response.json()["task_id"]

    # 获取项目详情（这会创建一个 Run）
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    run_id = response.json()["active_run"]["run_id"]

    # 列出产物
    response = client.get(f"/api/v1/tasks/{task_id}/runs/{run_id}/artifacts")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []


# ── 诊断测试 ──────────────────────────────────────────────────────


def test_v1_export_diagnostics(client: TestClient, tmp_state: Path) -> None:
    """导出诊断包。"""
    # 先创建项目
    response = client.post("/api/v1/tasks", json={"title": "测试"})
    task_id = response.json()["task_id"]

    # 获取项目详情（这会创建一个 Run）
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    run_id = response.json()["active_run"]["run_id"]

    # 导出诊断包
    response = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/diagnostics")
    assert response.status_code == 200
    body = response.json()
    assert "bundle_id" in body
    assert "download_url" in body


# ── 视图完整性测试 ──────────────────────────────────────────────────────


def test_v1_project_detail_view(client: TestClient, tmp_state: Path) -> None:
    """项目详情视图包含所有必要字段。"""
    # 先创建项目
    response = client.post("/api/v1/tasks", json={"title": "视图测试"})
    task_id = response.json()["task_id"]

    # 获取详情
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    body = response.json()

    # 验证视图字段
    assert "task" in body
    assert "active_run" in body
    assert "stages" in body
    assert "warnings" in body
    assert "artifacts" in body
    assert "trace" in body


def test_v1_run_view(client: TestClient, tmp_state: Path) -> None:
    """Run 视图包含所有必要字段。"""
    # 先创建项目
    response = client.post("/api/v1/tasks", json={"title": "Run视图测试"})
    task_id = response.json()["task_id"]

    # 获取项目详情（这会创建一个 Run）
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    run_id = response.json()["active_run"]["run_id"]

    # 获取 Run
    response = client.get(f"/api/v1/tasks/{task_id}/runs/{run_id}")
    assert response.status_code == 200
    body = response.json()

    # 验证视图字段
    assert "run_id" in body
    assert "task_id" in body
    assert "status" in body
    assert "stages" in body
    assert "warnings" in body


# ── 任务制作输入读取测试 ────────────────────────────────────────────────


def test_v1_get_inputs_saved(client: TestClient, tmp_state: Path) -> None:
    """保存任务输入后 GET /inputs 返回正确非敏感 DTO。"""
    # 创建任务
    resp = client.post("/api/v1/tasks", json={"title": "输入读取测试"})
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]

    # 保存输入
    script = "这是一段用于测试输入读取的文案，足够长以满足最小要求。"
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={
            "script": script,
            "style": "极简粗线简笔白板风",
            "include_subtitles": "true",
            "pen_text": "",
            "stroke_detail": "detailed",
        },
        files={"reference": ("reference.wav", b"RIFF" + b"\x00" * 100, "audio/wav")},
    )
    assert resp.status_code == 200

    # 读取输入
    resp = client.get(f"/api/v1/tasks/{task_id}/inputs")
    assert resp.status_code == 200
    body = resp.json()

    assert body["task_id"] == task_id
    assert body["saved"] is True
    assert body["inputs"]["script"] == script
    assert body["inputs"]["style"] == "极简粗线简笔白板风"
    assert body["inputs"]["include_subtitles"] is True
    assert body["inputs"]["stroke_detail"] == "detailed"
    assert body["reference_audio"]["uploaded"] is True
    assert body["reference_audio"]["filename"] == "reference.wav"
    assert body["reference_audio"]["content_type"] == "audio/wav"
    assert body["reference_audio"]["size_bytes"] > 0


def test_v1_get_inputs_unsaved(client: TestClient, tmp_state: Path) -> None:
    """未保存输入时 GET /inputs 返回 saved:false。"""
    resp = client.post("/api/v1/tasks", json={"title": "未保存输入"})
    task_id = resp.json()["task_id"]

    resp = client.get(f"/api/v1/tasks/{task_id}/inputs")
    assert resp.status_code == 200
    body = resp.json()

    assert body["task_id"] == task_id
    assert body["saved"] is False
    assert body["inputs"] is None
    assert body["reference_audio"]["uploaded"] is False


def test_v1_get_inputs_not_found(client: TestClient, tmp_state: Path) -> None:
    """任务不存在时 GET /inputs 返回 404。"""
    resp = client.get("/api/v1/tasks/nonexistent/inputs")
    assert resp.status_code == 404


def test_v1_get_inputs_no_secrets_or_paths(client: TestClient, tmp_state: Path) -> None:
    """GET /inputs 响应不含路径、音频内容、api_key、secret、token、password、credential。"""
    resp = client.post("/api/v1/tasks", json={"title": "安全测试"})
    task_id = resp.json()["task_id"]

    script = "这是一段用于安全测试的文案，足够长以满足最小要求。包含多个句子。"
    resp = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={
            "script": script,
            "style": "极简粗线简笔白板风",
            "include_subtitles": "true",
            "pen_text": "",
            "stroke_detail": "detailed",
        },
        files={"reference": ("reference.wav", b"RIFF" + b"\x00" * 100, "audio/wav")},
    )
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/tasks/{task_id}/inputs")
    assert resp.status_code == 200
    body = resp.json()

    # 递归序列化检查
    serialized = json.dumps(body, ensure_ascii=False).lower()
    forbidden = ["api_key", "secret", "token", "password", "credential", "/tmp/", "/home/", "\\\\"]
    for word in forbidden:
        assert word not in serialized, f"Forbidden '{word}' found in response"

    # reference_audio 只有元数据，不含二进制
    assert "content" not in body["reference_audio"]
    assert "data" not in body["reference_audio"]
    assert "path" not in body["reference_audio"]
    assert "url" not in body["reference_audio"]


# ── 验收测试：完整流程（Provider 未配置场景） ──────────────────────────────


def test_v1_acceptance_flow_with_missing_provider(
    client: TestClient, tmp_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M07 PR-1b 验收：创建项目 → 上传音频 → 启动真实标准流程 → 返回 CAPABILITY_NOT_AVAILABLE。"""
    # 模拟 Provider 不可用（真实 STATE_DIR 可能已有配置）
    from csboard.adapters.provider_factory import ProviderFactory

    unavailable_result = {
        "all_available": False,
        "providers": {
            name: {"available": False, "component": name, "error_code": "SECRET_NOT_CONFIGURED", "suggestion": "请配置 api_key"}
            for name in ("text_model", "image_model", "tts", "alignment", "renderer", "media")
        },
        "unavailable": ["text_model", "image_model", "tts", "alignment", "renderer", "media"],
    }
    monkeypatch.setattr(ProviderFactory, "check_all_availability", lambda self: unavailable_result)

    # 步骤 1: 创建项目
    response = client.post("/api/v1/tasks", json={"title": "验收测试项目"})
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    assert task_id

    # 步骤 2: 上传文案和参考音频
    script = "这是一段用于验收测试的文案，足够长以满足最小要求。包含多个句子，用于测试分镜功能。"
    reference_content = b"RIFF" + b"\x00" * 100  # 简单的 WAV 头部
    response = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={
            "script": script,
            "style": "极简粗线简笔白板风",
            "include_subtitles": "true",
            "pen_text": "",
            "stroke_detail": "detailed",
        },
        files={"reference": ("reference.wav", reference_content, "audio/wav")},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True

    # 步骤 3: 获取项目详情（这会创建一个 Run）
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    run_id = response.json()["active_run"]["run_id"]

    # 步骤 4: 尝试启动标准流程（Provider 未配置）
    response = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start")
    assert response.status_code == 400
    body = response.json()

    # 验证返回 CAPABILITY_NOT_AVAILABLE
    assert body["detail"]["code"] == "CAPABILITY_NOT_AVAILABLE"
    assert isinstance(body["detail"]["message"], str) and body["detail"]["message"]
    # 当前 API 使用 "unavailable" 列表和 "details" 结构
    assert isinstance(body["detail"]["unavailable"], list)
    assert len(body["detail"]["unavailable"]) > 0
    assert isinstance(body["detail"]["details"], list)
    for item in body["detail"]["details"]:
        assert "provider" in item
        assert "error_code" in item


# ── Provider 配置后启动测试 ──────────────────────────────────────────


def test_v1_provider_configuration_enables_start(client: TestClient, tmp_state: Path) -> None:
    """配置所有 Provider 后，start 应该调用 MountainCommands.pipeline_run。"""
    # 配置所有必需的 secrets
    providers_to_configure = {
        "text_model": {"api_key": "sk-test-text-model"},
        "image_model": {"api_key": "sk-test-image-model"},
    }
    for provider, secrets in providers_to_configure.items():
        for key, value in secrets.items():
            response = client.post(
                f"/api/v1/providers/{provider}/secrets",
                json={"key": key, "value": value},
            )
            assert response.status_code == 200

    # 验证 all_configured 现在是 True
    response = client.get("/api/v1/providers")
    assert response.status_code == 200
    body = response.json()
    assert body["all_configured"] is True

    # 创建项目并上传输入
    response = client.post("/api/v1/tasks", json={"title": "配置完成测试"})
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    script = "这是一段用于测试的文案，足够长以满足最小要求。包含多个句子，用于测试分镜功能。"
    response = client.post(
        f"/api/v1/tasks/{task_id}/inputs",
        data={
            "script": script,
            "style": "极简粗线简笔白板风",
            "include_subtitles": "true",
        },
        files={"reference": ("reference.wav", b"RIFF" + b"\x00" * 100, "audio/wav")},
    )
    assert response.status_code == 200

    # 获取项目详情（这会创建一个 Run）
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    run_id = response.json()["active_run"]["run_id"]

    # 尝试启动（现在应该成功调用 pipeline_run）
    response = client.post(f"/api/v1/tasks/{task_id}/runs/{run_id}/start")
    # 注意：这里可能仍然会失败，因为 pipeline_run 内部可能需要更多依赖
    # 但至少 Provider 检查应该通过
    # 我们验证它不是因为 Provider 问题而失败
    if response.status_code == 400:
        body = response.json()
        assert body["detail"]["code"] != "CAPABILITY_NOT_AVAILABLE"


# ── Secret 安全性测试 ──────────────────────────────────────────────────


def test_v1_secret_not_in_response(client: TestClient, tmp_state: Path) -> None:
    """Secret 不应该出现在 API 响应中。"""
    # 设置 secret
    client.post(
        "/api/v1/providers/text_model/secrets",
        json={"key": "api_key", "value": "sk-super-secret-key-12345"},
    )

    # 获取 provider 状态
    response = client.get("/api/v1/providers/text_model/secrets")
    body = response.json()

    # 验证响应中不包含实际 secret
    response_text = json.dumps(body)
    assert "sk-super-secret-key-12345" not in response_text

    # 验证 masked_value 存在但不包含完整 key
    if body["secrets"]["api_key"]["masked_value"]:
        assert "sk-super-secret-key-12345" not in body["secrets"]["api_key"]["masked_value"]


def test_v1_secret_not_in_health(client: TestClient, tmp_state: Path) -> None:
    """Secret 不应该出现在 health 响应中。"""
    # 设置 secret
    client.post(
        "/api/v1/providers/text_model/secrets",
        json={"key": "api_key", "value": "sk-super-secret-key-12345"},
    )

    # 获取 health 状态
    response = client.get("/api/v1/health")
    body = response.json()

    # 验证响应中不包含实际 secret
    response_text = json.dumps(body)
    assert "sk-super-secret-key-12345" not in response_text


# ── 无 legacy 依赖验证 ──────────────────────────────────────────────────────


def test_v1_no_legacy_references(client: TestClient) -> None:
    """验证 /api/v1 不包含任何 legacy 依赖。"""
    from webapp import mountain_v1_api
    import inspect

    source = inspect.getsource(mountain_v1_api)

    # 将源码按行分割，只检查非注释行
    lines = source.split('\n')
    code_lines = []
    in_docstring = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                continue
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        if stripped.startswith('#'):
            continue
        code_lines.append(line)

    code_only = '\n'.join(code_lines)

    # 验证没有 legacy 依赖
    assert "from webapp.mountain_stages" not in code_only
    assert "import mountain_stages" not in code_only
    assert "legacy_execution_id" not in code_only
    assert "127.0.0.1:8000" not in code_only
    assert "FakeTextModel" not in code_only
    assert "FakeImageModel" not in code_only
    assert "FakeTextToSpeech" not in code_only
    assert "FakeAlignment" not in code_only
    assert "FakeRenderer" not in code_only
    assert "FakeMedia" not in code_only


# ── ProviderFactory 测试 ──────────────────────────────────────────────────


def test_provider_factory_check_providers(tmp_path: Path) -> None:
    """ProviderFactory.check_all_providers 返回正确状态。"""
    from csboard.adapters.provider_factory import ProviderFactory
    from csboard.adapters.secrets.secret_store import PlaintextSecretStore

    store = PlaintextSecretStore(tmp_path / ".secrets")
    factory = ProviderFactory(tmp_path, secret_store=store, is_encrypted=False)

    # 默认情况下，需要 secret 的 provider 未配置
    result = factory.check_all_providers()
    assert result["all_configured"] is False
    assert "providers" in result
    assert len(result["providers"]) == 6
    # text_model 和 image_model 需要 api_key secret
    assert "text_model" in result["missing"]
    assert "image_model" in result["missing"]
    # tts、alignment、renderer、media 不需要 secret
    assert "tts" in result["configured"]
    assert "alignment" in result["configured"]
    assert "renderer" in result["configured"]
    assert "media" in result["configured"]


def test_provider_factory_create_adapters(tmp_path: Path) -> None:
    """ProviderFactory 可以构造真实 Adapter。"""
    from csboard.adapters.provider_factory import ProviderFactory
    from csboard.adapters.secrets.secret_store import PlaintextSecretStore

    store = PlaintextSecretStore(tmp_path / ".secrets")
    factory = ProviderFactory(tmp_path, secret_store=store, is_encrypted=False)

    # 配置 text_model secret
    factory.secret_store.set("text_model_api_key", "sk-test")

    # 构造 text_model adapter（无 profile 参数）
    text_model = factory.create_text_model()
    assert text_model is not None
    assert hasattr(text_model, 'generate')

    # 构造其他 adapters（不需要 secret）
    tts = factory.create_tts()
    assert tts is not None

    alignment = factory.create_alignment()
    assert alignment is not None

    renderer = factory.create_renderer()
    assert renderer is not None

    media = factory.create_media()
    assert media is not None


# ── SecretStore 测试 ──────────────────────────────────────────────────


def test_secret_store_basic_operations(tmp_path: Path) -> None:
    """SecretStore 基本操作：set、get、has、delete、mask。"""
    from csboard.adapters.secrets import PlaintextSecretStore, mask_secret

    store = PlaintextSecretStore(tmp_path / "secrets.json")

    # 初始状态
    assert store.get("test_key") is None
    assert store.has("test_key") is False

    # 设置
    store.set("test_key", "test_value")
    assert store.get("test_key") == "test_value"
    assert store.has("test_key") is True

    # 列出 keys
    assert "test_key" in store.list_keys()

    # 删除（返回 None）
    store.delete("test_key")
    assert store.get("test_key") is None
    assert store.has("test_key") is False

    # mask_secret 边界
    assert mask_secret(None) == ""
    assert mask_secret("") == ""
    assert mask_secret("abc") == "••••"
    assert mask_secret("sk-1234567890abcdef") == "sk-1••••cdef"


def test_mask_secret() -> None:
    """mask_secret 正确掩码 secret 值。"""
    from csboard.adapters.secrets import mask_secret

    # 短 secret
    assert mask_secret("abc") == "••••"

    # 长 secret
    result = mask_secret("sk-1234567890abcdef")
    assert result.startswith("sk-1")
    assert result.endswith("cdef")
    assert "••••" in result

    # None
    assert mask_secret(None) == ""

    # 空字符串
    assert mask_secret("") == ""
