"""mountain_service_api 测试。

覆盖：
- Service CRUD
- activate/deactivate
- set-default
- probe
- secret set/delete
- service_id 校验
- 未知字段拒绝
- public DTO 脱敏
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from webapp.mountain_server import create_app


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    app = create_app(tmp_path)
    return TestClient(app)


def test_create_service(client: TestClient):
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test Service",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "required_secrets": ["api_key"],
    }
    resp = client.post("/api/v1/services", json=svc_data)
    assert resp.status_code == 200
    data = resp.json()
    assert data["service_id"] == "test-svc"
    assert data["capability"] == "text_generation"


def test_list_services(client: TestClient):
    resp = client.get("/api/v1/services")
    assert resp.status_code == 200
    assert "items" in resp.json()


def test_get_service(client: TestClient):
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
    }
    client.post("/api/v1/services", json=svc_data)
    resp = client.get("/api/v1/services/test-svc")
    assert resp.status_code == 200
    assert resp.json()["service_id"] == "test-svc"


def test_update_service(client: TestClient):
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Old Name",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
    }
    client.post("/api/v1/services", json=svc_data)
    resp = client.patch("/api/v1/services/test-svc", json={"display_name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "New Name"


def test_delete_service(client: TestClient):
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
    }
    client.post("/api/v1/services", json=svc_data)
    # 先停用再删除（默认+启用的服务不能直接删除）
    client.post("/api/v1/services/test-svc/deactivate")
    resp = client.delete("/api/v1/services/test-svc")
    assert resp.status_code == 200


def test_activate_deactivate(client: TestClient):
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
    }
    client.post("/api/v1/services", json=svc_data)

    resp = client.post("/api/v1/services/test-svc/deactivate")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    resp = client.post("/api/v1/services/test-svc/activate")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True


def test_set_default(client: TestClient):
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
    }
    client.post("/api/v1/services", json=svc_data)
    resp = client.post("/api/v1/services/test-svc/default")
    assert resp.status_code == 200
    assert resp.json()["is_default"] is True


def test_secret_set_and_list(client: TestClient):
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "required_secrets": ["api_key"],
    }
    client.post("/api/v1/services", json=svc_data)

    # 设置 secret
    resp = client.post("/api/v1/services/test-svc/secrets", json={"key": "api_key", "value": "sk-123"})
    assert resp.status_code == 200

    # 列出 secrets
    resp = client.get("/api/v1/services/test-svc/secrets")
    assert resp.status_code == 200
    data = resp.json()
    # 不应包含明文
    assert "sk-123" not in json.dumps(data)


def test_service_id_validation(client: TestClient):
    """service_id 路径穿越拒绝。"""
    for bad_id in ["../etc", "svc/id", "svc\\id", "..", ""]:
        svc_data = {
            "service_id": bad_id,
            "display_name": "Test",
            "capability": "text_generation",
            "adapter_type": "openai_compatible",
        }
        resp = client.post("/api/v1/services", json=svc_data)
        assert resp.status_code == 400


def test_unknown_field_rejected(client: TestClient):
    """未知字段拒绝。"""
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
    }
    client.post("/api/v1/services", json=svc_data)
    resp = client.patch("/api/v1/services/test-svc", json={"unknown_field": "value"})
    assert resp.status_code == 400


def test_public_dict_no_secrets(client: TestClient):
    """公开 DTO 不包含 secret 值。"""
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "config": {"api_key": "sk-secret", "model": "gpt-4o"},
        "required_secrets": ["api_key"],
    }
    client.post("/api/v1/services", json=svc_data)
    resp = client.get("/api/v1/services/test-svc")
    data = resp.json()
    config = data.get("config", {})
    # api_key 不应在 config 中
    assert "api_key" not in config or config["api_key"] != "sk-secret"
