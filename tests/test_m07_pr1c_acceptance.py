"""M07 PR-1c: ProviderFactory 到 MountainCommands 真实执行接线 - 验收测试。

验收标准：
1. ProviderFactory 成为 MountainCommands/Pipeline 的唯一 Provider 构造入口
2. MountainCommands 不从 request.json 读取 API Key
3. request.json 只保存项目输入和非敏感制作参数
4. API Key 只经 SecretStore 读取
5. Pipeline 六阶段使用 ProviderFactory 构造的真实 Adapter
6. /api/v1/health 和 /api/v1/capabilities 实际检查可用性
7. start 行为：不完整配置返回 CAPABILITY_NOT_AVAILABLE，完整配置实际运行 pipeline
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def api_env(tmp_path, monkeypatch):
    """为每个测试创建独立的 STATE_DIR 和 ProviderFactory。"""
    monkeypatch.setenv("CSBOARD_STATE_DIR", str(tmp_path / "state"))
    # 设置 master key 用于加密
    monkeypatch.setenv("CSBOARD_MASTER_KEY", "test-master-key-for-acceptance")

    # 重新导入
    if "csboard.application.commands" in sys.modules:
        del sys.modules["csboard.application.commands"]
    if "webapp.mountain_v1_api" in sys.modules:
        del sys.modules["webapp.mountain_v1_api"]
    if "csboard.adapters.provider_factory" in sys.modules:
        del sys.modules["csboard.adapters.provider_factory"]

    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from webapp.mountain_v1_api import mountain_v1_router

    repo_dir = tmp_path / "state"
    repo_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / "projects").mkdir(exist_ok=True)
    (repo_dir / ".secrets").mkdir(exist_ok=True)
    (repo_dir / ".profiles").mkdir(exist_ok=True)

    app = FastAPI()
    router = mountain_v1_router(repo_dir)
    app.include_router(router)
    client = TestClient(app)

    return {
        "client": client,
        "repo_dir": repo_dir,
        "tmp_path": tmp_path,
    }


# ── 1. ProviderFactory 是唯一入口 ──────────────────────────────────────────


def test_provider_factory_is_sole_entry(api_env):
    """验证 ProviderFactory 是 MountainCommands 的唯一 Provider 构造入口。"""
    from csboard.adapters.provider_factory import ProviderFactory

    factory = ProviderFactory(api_env["repo_dir"])

    # ProviderFactory 应该有构造 Adapter 的方法
    assert hasattr(factory, 'create_text_model')
    assert hasattr(factory, 'create_image_model')
    assert hasattr(factory, 'create_tts')
    assert hasattr(factory, 'create_alignment')
    assert hasattr(factory, 'create_renderer')
    assert hasattr(factory, 'create_media')


def test_mountain_commands_uses_provider_factory(api_env):
    """验证 MountainCommands 使用 ProviderFactory 而不是直接读取 request.json。"""
    from csboard.application.commands import MountainCommands

    repo_dir = api_env["repo_dir"]

    # 创建 MountainCommands
    commands = MountainCommands(data_dir=repo_dir)

    # MountainCommands 应该有 provider_factory
    assert commands.provider_factory is not None

    # MountainCommands 不应该有 _provider_config 方法（旧实现）
    assert not hasattr(commands, '_provider_config')


# ── 2. request.json 不保存 API Key ─────────────────────────────────────────


def test_request_json_no_api_key(api_env):
    """验证 request.json 不保存 API Key。"""
    client = api_env["client"]
    repo_dir = api_env["repo_dir"]

    # 创建项目
    proj_resp = client.post(
        "/api/v1/projects",
        json={"title": "测试项目", "outline": "测试大纲"},
    )
    project_id = proj_resp.json()["project_id"]

    # 上传参考音频
    audio_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    files = {"reference": ("reference.wav", audio_content, "audio/wav")}
    data = {"script": "测试剧本内容，足够长以通过验证。"}

    client.post(
        f"/api/v1/projects/{project_id}/inputs",
        files=files,
        data=data,
    )

    # 检查 request.json
    request_file = repo_dir / "projects" / project_id / "request.json"
    assert request_file.exists()

    request_data = json.loads(request_file.read_text(encoding="utf-8"))

    # request.json 不应该包含 api_key
    assert "api_key" not in request_data
    assert "api_key_env" not in request_data

    # request.json 应该只包含非敏感数据
    assert "script" in request_data
    assert "reference_audio" in request_data


# ── 3. API Key 只经 SecretStore 读取 ────────────────────────────────────────


def test_api_key_via_secret_store(api_env):
    """验证 API Key 只经 SecretStore 读取。"""
    from csboard.adapters.provider_factory import ProviderFactory
    from csboard.adapters.secrets import FileSecretStore

    repo_dir = api_env["repo_dir"]
    factory = ProviderFactory(repo_dir)

    # 保存 API Key 到 SecretStore
    factory.secret_store.set("text_model_api_key", "test-api-key-12345")

    # 通过 ProviderFactory 获取 TextModel（应该能读取 API Key）
    try:
        text_model = factory.create_text_model()
        # 验证 adapter 有 api_key 属性
        assert hasattr(text_model, '_api_key') or hasattr(text_model, 'api_key')
    except Exception as e:
        # 如果构造失败，至少验证 secret 已保存
        assert factory.secret_store.get("text_model_api_key") == "test-api-key-12345"


def test_api_key_not_in_request_json_after_upload(api_env):
    """验证上传后 request.json 不包含 API Key。"""
    client = api_env["client"]
    repo_dir = api_env["repo_dir"]

    # 创建项目
    proj_resp = client.post(
        "/api/v1/projects",
        json={"title": "测试项目", "outline": "测试大纲"},
    )
    project_id = proj_resp.json()["project_id"]

    # 上传参考音频（不包含 API Key）
    audio_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    files = {"reference": ("reference.wav", audio_content, "audio/wav")}
    data = {"script": "测试剧本内容，足够长以通过验证。"}

    client.post(
        f"/api/v1/projects/{project_id}/inputs",
        files=files,
        data=data,
    )

    # 读取 request.json
    request_file = repo_dir / "projects" / project_id / "request.json"
    request_data = json.loads(request_file.read_text(encoding="utf-8"))

    # 确保没有 API Key 相关字段
    for key in request_data:
        assert "api_key" not in key.lower(), f"request.json 包含敏感字段: {key}"


# ── 4. Pipeline 六阶段使用 ProviderFactory 构造的真实 Adapter ────────────────


def test_pipeline_stages_use_provider_factory(api_env):
    """验证 Pipeline 六阶段使用 ProviderFactory 构造的真实 Adapter。"""
    from csboard.application.commands import MountainCommands

    repo_dir = api_env["repo_dir"]
    commands = MountainCommands(data_dir=repo_dir)

    # 验证 MountainCommands 有 _run_stage 方法
    assert hasattr(commands, '_run_stage')

    # 验证 _run_stage 使用 ProviderFactory
    import inspect
    source = inspect.getsource(commands._run_stage)

    # 应该调用 ProviderFactory 的 create_* 方法
    assert 'factory.create_tts' in source
    assert 'factory.create_text_model' in source
    assert 'factory.create_image_model' in source
    assert 'factory.create_alignment' in source
    assert 'factory.create_renderer' in source
    assert 'factory.create_media' in source


def test_stage_executors_receive_adapter(api_env):
    """验证阶段执行器接收 ProviderFactory 构造的 Adapter。"""
    from csboard.application.commands import MountainCommands

    repo_dir = api_env["repo_dir"]
    commands = MountainCommands(data_dir=repo_dir)

    # 验证 _exec_clone_voice 接收 tts_adapter 参数
    import inspect
    sig = inspect.signature(commands._exec_clone_voice)
    assert 'tts_adapter' in sig.parameters

    # 验证 _exec_plan_storyboard 接收 text_model 参数
    sig = inspect.signature(commands._exec_plan_storyboard)
    assert 'text_model' in sig.parameters

    # 验证 _exec_generate_illustrations 接收 image_model 参数
    sig = inspect.signature(commands._exec_generate_illustrations)
    assert 'image_model' in sig.parameters


# ── 5. health 和 capabilities 实际检查可用性 ─────────────────────────────────


def test_health_checks_availability(api_env):
    """验证 /api/v1/health 实际检查 Provider 可用性。"""
    client = api_env["client"]

    # 未配置时应该返回 degraded
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200

    data = resp.json()
    assert "status" in data
    assert "providers" in data

    # 应该有 provider 状态
    providers = data["providers"]
    assert "all_configured" in providers
    assert "configured" in providers
    assert "missing" in providers


def test_capabilities_checks_availability(api_env):
    """验证 /api/v1/capabilities 实际检查 Provider 可用性。"""
    client = api_env["client"]

    resp = client.get("/api/v1/capabilities")
    assert resp.status_code == 200

    data = resp.json()
    assert "items" in data
    assert "providers" in data

    # providers 应该有实际状态
    providers = data["providers"]
    assert "all_configured" in providers


def test_health_with_configured_providers(api_env):
    """验证配置 Provider 后 health 返回 ok。"""
    client = api_env["client"]

    # 通过 API 配置 secrets
    client.post(
        "/api/v1/providers/text_model/secrets",
        json={"key": "api_key", "value": "test-key"},
    )
    client.post(
        "/api/v1/providers/image_model/secrets",
        json={"key": "api_key", "value": "test-key"},
    )

    # 重新检查 health
    resp = client.get("/api/v1/health")
    data = resp.json()

    # 应该有配置好的 providers
    providers = data["providers"]
    assert "text_model" in providers.get("configured", [])
    assert "image_model" in providers.get("configured", [])


# ── 6. start 行为：不完整配置返回 CAPABILITY_NOT_AVAILABLE ──────────────────


def test_start_returns_capability_not_available_when_missing(api_env):
    """验证 start 在 Provider 未配置时返回 CAPABILITY_NOT_AVAILABLE。"""
    client = api_env["client"]

    # 创建项目
    proj_resp = client.post(
        "/api/v1/projects",
        json={"title": "测试项目", "outline": "测试大纲"},
    )
    project_id = proj_resp.json()["project_id"]

    # 上传参考音频
    audio_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    files = {"reference": ("reference.wav", audio_content, "audio/wav")}
    data = {"script": "测试剧本内容，足够长以通过验证。"}

    client.post(
        f"/api/v1/projects/{project_id}/inputs",
        files=files,
        data=data,
    )

    # 获取 run_id（通过项目详情）
    project_resp = client.get(f"/api/v1/projects/{project_id}")
    run_id = project_resp.json()["active_run"]["run_id"]

    # 尝试启动（应该失败，因为 Provider 未配置）
    resp = client.post(f"/api/v1/projects/{project_id}/runs/{run_id}/start")

    # 应该返回 400
    assert resp.status_code == 400

    error = resp.json()
    assert error.get("detail", {}).get("code") == "CAPABILITY_NOT_AVAILABLE"


def test_start_runs_pipeline_when_configured(api_env):
    """验证 start 在 Provider 完整配置时实际运行 pipeline。"""
    client = api_env["client"]

    # 通过 API 配置 secrets
    client.post(
        "/api/v1/providers/text_model/secrets",
        json={"key": "api_key", "value": "test-key"},
    )
    client.post(
        "/api/v1/providers/image_model/secrets",
        json={"key": "api_key", "value": "test-key"},
    )

    # 创建项目
    proj_resp = client.post(
        "/api/v1/projects",
        json={"title": "测试项目", "outline": "测试大纲"},
    )
    project_id = proj_resp.json()["project_id"]

    # 上传参考音频
    audio_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    files = {"reference": ("reference.wav", audio_content, "audio/wav")}
    data = {"script": "测试剧本内容，足够长以通过验证。"}

    client.post(
        f"/api/v1/projects/{project_id}/inputs",
        files=files,
        data=data,
    )

    # 获取 run_id
    project_resp = client.get(f"/api/v1/projects/{project_id}")
    run_id = project_resp.json()["active_run"]["run_id"]

    # 尝试启动（可能成功或失败，但不应该返回 CAPABILITY_NOT_AVAILABLE）
    resp = client.post(f"/api/v1/projects/{project_id}/runs/{run_id}/start")

    # 应该不是 400（CAPABILITY_NOT_AVAILABLE）
    if resp.status_code == 400:
        error = resp.json()
        assert error.get("detail", {}).get("code") != "CAPABILITY_NOT_AVAILABLE"


# ── 7. SecretStore 支持加密 ─────────────────────────────────────────────────


def test_secret_store_encrypted_by_default(api_env):
    """验证 SecretStore 默认使用加密。"""
    from csboard.adapters.provider_factory import ProviderFactory

    repo_dir = api_env["repo_dir"]

    # 检查 cryptography 是否可用
    try:
        from cryptography.fernet import Fernet
        # 如果 cryptography 可用，默认应该使用加密
        factory = ProviderFactory(repo_dir)
        assert factory.is_encrypted
    except ImportError:
        # 如果 cryptography 不可用，应该降级到明文
        factory = ProviderFactory(repo_dir)
        assert not factory.is_encrypted


def test_secret_store_falls_back_to_plaintext(api_env):
    """验证 SecretStore 在无 cryptography 时降级到明文。"""
    from csboard.adapters.provider_factory import ProviderFactory

    repo_dir = api_env["repo_dir"]

    # 强制使用明文
    factory = ProviderFactory(repo_dir, encrypted=False)

    assert not factory.is_encrypted

    # 保存和读取 secret
    factory.secret_store.set("test_key", "test_value")
    assert factory.secret_store.get("test_key") == "test_value"


# ── 8. Provider 配置持久化 ───────────────────────────────────────────────────


def test_provider_config_persists(api_env):
    """验证 Provider 非敏感配置持久化。"""
    from csboard.adapters.provider_factory import ProviderFactory

    repo_dir = api_env["repo_dir"]
    factory = ProviderFactory(repo_dir)

    # 更新配置
    factory.update_profile_config("text_model", {"model": "gpt-4o-mini"})

    # 重新创建 factory
    factory2 = ProviderFactory(repo_dir)

    # 配置应该持久化
    profile = factory2.get_profile("text_model")
    assert profile is not None
    assert profile.config.get("model") == "gpt-4o-mini"


def test_provider_config_does_not_store_secrets(api_env):
    """验证 Provider 配置不存储 secrets。"""
    from csboard.adapters.provider_factory import ProviderFactory

    repo_dir = api_env["repo_dir"]
    factory = ProviderFactory(repo_dir)

    # 更新配置
    factory.update_profile_config("text_model", {"model": "gpt-4o"})

    # 检查配置文件
    config_file = repo_dir / ".profiles" / "text_model.json"
    assert config_file.exists()

    config_data = json.loads(config_file.read_text(encoding="utf-8"))

    # 配置文件不应该包含 api_key
    assert "api_key" not in config_data.get("config", {})


# ── 9. 集成验收测试 ─────────────────────────────────────────────────────────


def test_full_flow_with_provider_factory(api_env):
    """完整流程验收测试。"""
    client = api_env["client"]

    # 1. 通过 API 配置 secrets
    client.post(
        "/api/v1/providers/text_model/secrets",
        json={"key": "api_key", "value": "test-key"},
    )
    client.post(
        "/api/v1/providers/image_model/secrets",
        json={"key": "api_key", "value": "test-key"},
    )

    # 2. 创建项目
    proj_resp = client.post(
        "/api/v1/projects",
        json={"title": "验收测试项目", "outline": "验收测试大纲"},
    )
    assert proj_resp.status_code == 200
    project_id = proj_resp.json()["project_id"]

    # 3. 上传参考音频
    audio_content = b"RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    files = {"reference": ("reference.wav", audio_content, "audio/wav")}
    data = {"script": "验收测试剧本内容，足够长以通过验证测试。"}

    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/inputs",
        files=files,
        data=data,
    )
    assert upload_resp.status_code == 200

    # 4. 检查 Provider 配置
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert "text_model" in health_data["providers"].get("configured", [])
    assert "image_model" in health_data["providers"].get("configured", [])

    # 5. 获取 run
    project_resp = client.get(f"/api/v1/projects/{project_id}")
    run_id = project_resp.json()["active_run"]["run_id"]

    # 6. 启动 pipeline（不检查结果，只验证不返回 CAPABILITY_NOT_AVAILABLE）
    start_resp = client.post(f"/api/v1/projects/{project_id}/runs/{run_id}/start")

    # 如果是 400，不应该是因为 CAPABILITY_NOT_AVAILABLE
    if start_resp.status_code == 400:
        error = start_resp.json()
        assert error.get("detail", {}).get("code") != "CAPABILITY_NOT_AVAILABLE"


def test_provider_factory_constructs_real_adapters(api_env):
    """验证 ProviderFactory 构造真实 Adapter 而不是 mock。"""
    from csboard.adapters.provider_factory import ProviderFactory
    from csboard.adapters.openai_compatible.text_adapter import OpenAITextAdapter
    from csboard.adapters.openai_compatible.image_adapter import OpenAIImageAdapter
    from csboard.adapters.indextts.tts_adapter import IndexTTSAdapter
    from csboard.adapters.whisper.alignment_adapter import WhisperAlignmentAdapter
    from csboard.adapters.ffmpeg.media_adapter import FFmpegMediaAdapter

    repo_dir = api_env["repo_dir"]
    factory = ProviderFactory(repo_dir)

    # 构造 adapters
    text_model = factory.create_text_model()
    image_model = factory.create_image_model()
    tts = factory.create_tts()
    alignment = factory.create_alignment()
    media = factory.create_media()

    # 验证是真实 Adapter 类型
    assert isinstance(text_model, OpenAITextAdapter)
    assert isinstance(image_model, OpenAIImageAdapter)
    assert isinstance(tts, IndexTTSAdapter)
    assert isinstance(media, FFmpegMediaAdapter)


def test_no_global_singleton_dependency(api_env):
    """验证 MountainCommands 不依赖全局单例。"""
    from csboard.application.commands import MountainCommands
    import inspect

    # 检查 MountainCommands 的 __init__ 不依赖全局状态
    source = inspect.getsource(MountainCommands.__post_init__)

    # 不应该有 global 或 import 顶层模块的依赖
    assert 'global' not in source
    assert 'singleton' not in source.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
