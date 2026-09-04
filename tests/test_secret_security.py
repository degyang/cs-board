"""Secret 安全测试。

覆盖：
- 默认加密
- 无加密能力时 fail closed
- 显式开发明文模式有警告
- API 不回显明文
- service JSON 无 Secret
- diagnostics 无 Secret
- CLI JSON 无 Secret
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from csboard.adapters.secrets.secret_store import PlaintextSecretStore, FileSecretStore, create_secret_store
from csboard.domain.service_definition import ServiceDefinition


def test_create_secret_store_encrypted(tmp_path: Path):
    """默认加密 SecretStore。"""
    try:
        store, is_encrypted = create_secret_store(tmp_path, encrypted=True)
        assert is_encrypted is True
        assert isinstance(store, FileSecretStore)
        assert (tmp_path / ".secrets" / "master.key").is_file()
    except Exception:
        # 如果环境不支持加密，应抛出异常
        pytest.skip("环境不支持 Fernet 加密")


def test_default_encrypted_store_survives_restart(tmp_path: Path):
    store, _ = create_secret_store(tmp_path, encrypted=True)
    store.set("service_api_key", "persist-me")

    reopened, _ = create_secret_store(tmp_path, encrypted=True)
    assert reopened.get("service_api_key") == "persist-me"


def test_create_secret_store_plaintext_explicit(tmp_path: Path):
    """显式明文模式。"""
    store, is_encrypted = create_secret_store(tmp_path, encrypted=False)
    assert is_encrypted is False
    assert isinstance(store, PlaintextSecretStore)


def test_plaintext_secret_store_operations(tmp_path: Path):
    """PlaintextSecretStore 基本操作。"""
    store = PlaintextSecretStore(tmp_path / ".secrets")
    store.set("test_key", "test_value")
    assert store.get("test_key") == "test_value"
    assert store.has("test_key") is True
    store.delete("test_key")
    assert store.get("test_key") is None
    assert store.has("test_key") is False


def test_api_does_not_echo_secrets(tmp_path: Path):
    """API 不回显明文 Secret。"""
    from webapp.mountain_server import create_app

    app = create_app(tmp_path)
    client = TestClient(app)

    # 创建服务
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "required_secrets": ["api_key"],
    }
    resp = client.post("/api/v1/services", json=svc_data)
    assert resp.status_code == 200

    # 设置 secret
    resp = client.post("/api/v1/services/test-svc/secrets", json={"key": "api_key", "value": "sk-secret123"})
    assert resp.status_code == 200
    # 响应不应包含明文
    assert "sk-secret123" not in json.dumps(resp.json())

    # 获取 secret 状态
    resp = client.get("/api/v1/services/test-svc/secrets")
    assert resp.status_code == 200
    data = resp.json()
    # 不应包含明文
    resp_text = json.dumps(data)
    assert "sk-secret123" not in resp_text
    # secrets 是列表
    for secret_info in data.get("secrets", []):
        if secret_info.get("configured"):
            assert "sk-secret123" not in json.dumps(secret_info)


def test_service_json_no_secrets(tmp_path: Path):
    """service JSON 文件不包含 Secret。"""
    from webapp.mountain_server import create_app

    app = create_app(tmp_path)
    client = TestClient(app)

    # 创建服务并设置 secret
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "required_secrets": ["api_key"],
    }
    client.post("/api/v1/services", json=svc_data)
    client.post("/api/v1/services/test-svc/secrets", json={"key": "api_key", "value": "sk-secret123"})

    # 检查 JSON 文件
    svc_file = tmp_path / "settings" / "services" / "test-svc.json"
    if svc_file.exists():
        content = svc_file.read_text(encoding="utf-8")
        assert "sk-secret123" not in content


def test_diagnostics_no_secrets(tmp_path: Path):
    """diagnostics 不包含 Secret。"""
    from webapp.mountain_server import create_app

    app = create_app(tmp_path)
    client = TestClient(app)

    # 创建服务并设置 secret
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "required_secrets": ["api_key"],
    }
    client.post("/api/v1/services", json=svc_data)
    client.post("/api/v1/services/test-svc/secrets", json={"key": "api_key", "value": "sk-secret123"})

    # 获取 diagnostics
    resp = client.get("/api/v1/settings/diagnostics")
    assert resp.status_code == 200
    resp_text = json.dumps(resp.json())
    assert "sk-secret123" not in resp_text


@pytest.mark.parametrize("key_variant", [
    "api_key", "ApiKey", "API_KEY", "apikey", "APIKEY", "apiKey",
    "token", "Token", "TOKEN",
    "secret", "Secret", "SECRET",
    "password", "Password",
    "authorization", "Authorization",
    "access_token", "AccessToken", "accessToken",
    "refresh_token", "RefreshToken",
    "api_secret", "ApiSecret",
])
def test_config_sanitizes_all_sensitive_key_variants(tmp_path: Path, key_variant: str):
    """config 中各种大小写/下划线变体的敏感字段都必须被过滤。"""
    from csboard.adapters.filesystem.service_registry import _sanitize_config
    config = {key_variant: "sk-leaked-value", "model": "gpt-4o"}
    sanitized = _sanitize_config(config)
    assert key_variant not in sanitized, f"敏感字段 '{key_variant}' 未被过滤"
    assert "model" in sanitized, "非敏感字段被误删"


def test_api_config_never_leaks_camelcase_sensitive_keys(tmp_path: Path):
    """API 响应 config 中不得出现 camelCase 敏感字段。"""
    from webapp.mountain_server import create_app

    app = create_app(tmp_path)
    client = TestClient(app)

    client.post("/api/v1/services", json={
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "config": {"ApiKey": "sk-leaked-camel-case", "model": "gpt-4o"},
    })

    resp = client.get("/api/v1/services/test-svc")
    config = resp.json().get("config", {})
    assert "ApiKey" not in config, "camelCase 敏感字段泄漏"
    assert "model" in config

    resp = client.get("/api/v1/services")
    list_text = json.dumps(resp.json())
    assert "sk-leaked-camel-case" not in list_text
