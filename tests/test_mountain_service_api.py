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


def test_update_service_provider_shape_and_multi_capability_metadata(client: TestClient):
    client.post("/api/v1/services", json={
        "service_id": "provider-service",
        "display_name": "Provider",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
    })
    resp = client.patch("/api/v1/services/provider-service", json={
        "capability": "image_generation",
        "adapter_type": "anthropic_compatible",
        "endpoint": "https://provider.example/v1",
        "model": "model-a, model-b",
        "config": {"capabilities": ["image_generation", "video_generation"]},
    })
    assert resp.status_code == 200
    assert resp.json()["capability"] == "image_generation"
    assert resp.json()["adapter_type"] == "anthropic_compatible"
    assert resp.json()["model"] == "model-a, model-b"
    assert resp.json()["config"]["capabilities"] == ["image_generation", "video_generation"]


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


# ── Item 11: Service create/update validation behavioral tests ─────────

def test_create_service_missing_required_fields(client: TestClient):
    """缺少必填字段应返回400。"""
    # 缺少 capability
    resp = client.post("/api/v1/services", json={
        "service_id": "test-svc",
        "display_name": "Test",
        "adapter_type": "openai_compatible",
    })
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_service_empty_service_id(client: TestClient):
    """空 service_id 应返回400。"""
    resp = client.post("/api/v1/services", json={
        "service_id": "",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
    })
    assert resp.status_code == 400


def test_update_service_not_found(client: TestClient):
    """更新不存在的服务应返回404。"""
    resp = client.patch("/api/v1/services/nonexistent", json={"display_name": "Test"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_delete_service_not_found(client: TestClient):
    """删除不存在的服务应返回404。"""
    resp = client.delete("/api/v1/services/nonexistent")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_create_service_duplicate_id(client: TestClient):
    """重复 service_id 应返回400。"""
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
    }
    resp1 = client.post("/api/v1/services", json=svc_data)
    assert resp1.status_code == 200

    resp2 = client.post("/api/v1/services", json=svc_data)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["error"]["message"].lower() or \
           "duplicate" in resp2.json()["error"]["message"].lower() or \
           "已存在" in resp2.json()["error"]["message"]


def test_create_service_with_config(client: TestClient):
    """创建服务时应正确保存 config。"""
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "config": {"temperature": 0.7, "max_tokens": 1000},
    }
    resp = client.post("/api/v1/services", json=svc_data)
    assert resp.status_code == 200

    # 验证 config 被保存
    resp = client.get("/api/v1/services/test-svc")
    assert resp.status_code == 200
    # config 应该存在但敏感字段被脱敏
    assert "config" in resp.json()


def test_probe_service(client: TestClient):
    """探测服务应返回可用性信息。"""
    svc_data = {
        "service_id": "test-svc",
        "display_name": "Test",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "endpoint": "https://api.openai.com/v1",
    }
    client.post("/api/v1/services", json=svc_data)

    resp = client.post("/api/v1/services/test-svc/probe")
    assert resp.status_code == 200
    data = resp.json()
    assert "available" in data
    assert "checked_at" in data


# ── MODEL-SERVICE-API-KEY-REWORK-018: 历史服务 API Key 设置 ────────────


def test_set_secret_legacy_openai_compatible_service(client: TestClient):
    """历史 openai_compatible 服务 required_secrets=[] 可以通过 API 设置 api_key。"""
    # 创建一个 required_secrets 为空的服务（模拟历史服务）
    svc_data = {
        "service_id": "legacy-openai",
        "display_name": "Legacy OpenAI",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "required_secrets": [],
    }
    resp = client.post("/api/v1/services", json=svc_data)
    assert resp.status_code == 200

    # 设置 api_key 应成功（adapter 标准 secret 白名单）
    resp = client.post("/api/v1/services/legacy-openai/secrets", json={"key": "api_key", "value": "sk-legacy-123"})
    assert resp.status_code == 200
    assert resp.json()["configured"] is True

    # 验证 secret 已配置
    resp = client.get("/api/v1/services/legacy-openai/secrets")
    assert resp.status_code == 200
    items = resp.json()["items"]
    api_key_item = next((s for s in items if s["secret_key"] == "api_key"), None)
    assert api_key_item is not None
    assert api_key_item["configured"] is True


def test_set_secret_legacy_service_unknown_key_rejected(client: TestClient):
    """历史服务仍然拒绝未知 secret key。"""
    svc_data = {
        "service_id": "legacy-openai",
        "display_name": "Legacy OpenAI",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "required_secrets": [],
    }
    client.post("/api/v1/services", json=svc_data)

    resp = client.post("/api/v1/services/legacy-openai/secrets", json={"key": "unknown_key", "value": "val"})
    assert resp.status_code == 400


def test_set_secret_other_adapter_rejects_api_key_via_api(client: TestClient):
    """other 适配器 required_secrets=[] 拒绝设置 api_key。"""
    svc_data = {
        "service_id": "other-svc",
        "display_name": "Other",
        "capability": "text_generation",
        "adapter_type": "other",
        "required_secrets": [],
    }
    client.post("/api/v1/services", json=svc_data)

    resp = client.post("/api/v1/services/other-svc/secrets", json={"key": "api_key", "value": "sk-should-fail"})
    assert resp.status_code == 400
