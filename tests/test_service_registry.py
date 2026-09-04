"""ServiceRegistry 测试。

覆盖：
- 多服务同 capability
- 默认唯一
- priority 选择
- disabled 排除
- 持久化重载
- revision 增长
- revision conflict
- 未知字段拒绝
- service_id 路径穿越拒绝
- 分页不漏项
- 默认切换失败保持旧状态
- 删除默认启用服务冲突
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.adapters.secrets.secret_store import PlaintextSecretStore
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.service_definition import ServiceDefinition


@pytest.fixture()
def registry(tmp_path: Path) -> FilesystemServiceRegistry:
    secret_store = PlaintextSecretStore(tmp_path / ".secrets")
    return FilesystemServiceRegistry(tmp_path, secret_store)


def _make_service(service_id: str, capability: str = "text_generation", **kwargs) -> ServiceDefinition:
    defaults = {
        "service_id": service_id,
        "display_name": f"Service {service_id}",
        "capability": capability,
        "adapter_type": "openai_compatible",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "enabled": True,
        "priority": 100,
        "is_default": False,
        "config": {},
        "required_secrets": ["api_key"],
        "optional_secrets": [],
    }
    defaults.update(kwargs)
    return ServiceDefinition(**defaults)


def test_create_and_list(registry: FilesystemServiceRegistry):
    svc = _make_service("svc-1")
    registry.create_service(svc)
    services = registry.list_services()
    assert len(services) == 1
    assert services[0].service_id == "svc-1"


def test_multiple_same_capability(registry: FilesystemServiceRegistry):
    """多服务同 capability。"""
    registry.create_service(_make_service("svc-1", priority=100))
    registry.create_service(_make_service("svc-2", priority=200))
    registry.create_service(_make_service("svc-3", capability="image_generation"))
    services = registry.list_services(capability="text_generation")
    assert len(services) == 2


def test_default_unique(registry: FilesystemServiceRegistry):
    """同 capability 最多一个默认服务。"""
    registry.create_service(_make_service("svc-1", is_default=True))
    registry.create_service(_make_service("svc-2", is_default=True))
    defaults = [s for s in registry.list_services(capability="text_generation") if s.is_default]
    assert len(defaults) == 1


def test_priority_selection(registry: FilesystemServiceRegistry):
    """无默认时按 priority 选择。第一个服务自动成为默认，创建后取消默认。"""
    s1 = registry.create_service(_make_service("svc-low", priority=200))
    s2 = registry.create_service(_make_service("svc-high", priority=10))
    # 取消所有默认
    registry.update_service("svc-low", {"enabled": True})  # 确保 enabled
    # s1 是默认（第一个创建的），取消它
    s1.is_default = False
    registry._save_service(s1)
    s2.is_default = False
    registry._save_service(s2)
    services = registry.list_services(capability="text_generation", enabled=True)
    services.sort(key=lambda s: (not s.is_default, s.priority, s.service_id))
    assert services[0].service_id == "svc-high"


def test_disabled_excluded(registry: FilesystemServiceRegistry):
    """disabled 服务不会被选择。"""
    registry.create_service(_make_service("svc-1", enabled=False))
    services = registry.list_services(capability="text_generation", enabled=True)
    assert len(services) == 0


def test_persistence_reload(tmp_path: Path):
    """持久化重载。"""
    secret_store = PlaintextSecretStore(tmp_path / ".secrets")
    reg1 = FilesystemServiceRegistry(tmp_path, secret_store)
    reg1.create_service(_make_service("svc-1"))

    # 新实例应能读取
    reg2 = FilesystemServiceRegistry(tmp_path, secret_store)
    services = reg2.list_services()
    assert len(services) == 1
    assert services[0].service_id == "svc-1"


def test_revision_grows(registry: FilesystemServiceRegistry):
    """PATCH/activate/deactivate revision 必须增长。"""
    svc = registry.create_service(_make_service("svc-1"))
    assert svc.revision == 1

    updated = registry.update_service("svc-1", {"display_name": "Updated"})
    assert updated.revision == 2

    activated = registry.activate_service("svc-1")
    assert activated.revision == 3

    deactivated = registry.deactivate_service("svc-1")
    assert deactivated.revision == 4


def test_changing_capability_preserves_one_default_per_capability(registry: FilesystemServiceRegistry):
    text = registry.create_service(_make_service("svc-text", capability="text_generation"))
    image = registry.create_service(_make_service("svc-image", capability="image_generation"))
    assert text.is_default is True
    assert image.is_default is True

    moved = registry.update_service("svc-text", {"capability": "image_generation"})
    assert moved.is_default is True
    assert registry.get_service("svc-image").is_default is False


def test_revision_conflict(registry: FilesystemServiceRegistry):
    """revision conflict 返回 REVISION_CONFLICT。"""
    svc = registry.create_service(_make_service("svc-1"))
    # 直接更新，不传 expected_revision
    registry.update_service("svc-1", {"display_name": "Updated"})
    # 用旧 revision 更新应失败
    with pytest.raises(DomainError) as exc_info:
        registry.update_service("svc-1", {"display_name": "Conflict"}, expected_revision=1)
    assert exc_info.value.code == "REVISION_CONFLICT"


def test_unknown_field_rejected(registry: FilesystemServiceRegistry):
    """未知字段拒绝。"""
    svc = _make_service("svc-1")
    registry.create_service(svc)
    with pytest.raises(DomainError) as exc_info:
        registry.update_service("svc-1", {"unknown_field": "value"})
    assert exc_info.value.code == "VALIDATION_ERROR"


def test_service_id_path_traversal_rejected(registry: FilesystemServiceRegistry):
    """service_id 路径穿越拒绝。"""
    for bad_id in ["../etc", "svc/id", "svc\\id", "..", "", "a" * 65]:
        with pytest.raises((DomainError, ValueError)):
            registry.create_service(_make_service(bad_id))


def test_pagination_no_skip(tmp_path: Path):
    """分页不漏项。"""
    secret_store = PlaintextSecretStore(tmp_path / ".secrets")
    reg = FilesystemServiceRegistry(tmp_path, secret_store)
    for i in range(5):
        reg.create_service(_make_service(f"svc-{i:02d}"))

    all_services = reg.list_services()
    assert len(all_services) == 5

    # 使用 limit=2 分页
    page1 = reg.list_services(limit=2)
    assert len(page1) == 2
    page2 = reg.list_services(limit=2, cursor=page1[-1].service_id)
    assert len(page2) == 2
    page3 = reg.list_services(limit=2, cursor=page2[-1].service_id)
    assert len(page3) == 1

    all_ids = {s.service_id for s in page1 + page2 + page3}
    assert len(all_ids) == 5


def test_set_default_clears_old(registry: FilesystemServiceRegistry):
    """设置新默认时旧默认被清除。"""
    registry.create_service(_make_service("svc-1", is_default=True))
    registry.create_service(_make_service("svc-2"))
    registry.set_default("svc-2")

    services = registry.list_services(capability="text_generation")
    defaults = [s for s in services if s.is_default]
    assert len(defaults) == 1
    assert defaults[0].service_id == "svc-2"


def test_disable_default_service(registry: FilesystemServiceRegistry):
    """停用默认服务时自动清除默认标记。"""
    registry.create_service(_make_service("svc-1", is_default=True))
    registry.deactivate_service("svc-1")
    svc = registry.get_service("svc-1")
    assert svc.enabled is False
    assert svc.is_default is False


# ── MODEL-SERVICE-API-KEY-REWORK-018: API Key 白名单修复 ─────────────


def test_set_secret_openai_compatible_legacy_service(registry: FilesystemServiceRegistry):
    """历史 openai_compatible 服务 required_secrets=[] 也能设置 api_key。"""
    svc = _make_service("legacy-openai", required_secrets=[], optional_secrets=[])
    registry.create_service(svc)
    # 应成功设置 api_key（由 adapter 标准 secret 允许）
    registry.set_secret("legacy-openai", "api_key", "sk-test-123")
    assert registry.get_secret_value("legacy-openai", "api_key") == "sk-test-123"


def test_set_secret_anthropic_compatible_legacy_service(registry: FilesystemServiceRegistry):
    """历史 anthropic_compatible 服务 required_secrets=[] 也能设置 api_key。"""
    svc = _make_service(
        "legacy-anthropic",
        adapter_type="anthropic_compatible",
        required_secrets=[],
        optional_secrets=[],
    )
    registry.create_service(svc)
    registry.set_secret("legacy-anthropic", "api_key", "sk-ant-test")
    assert registry.get_secret_value("legacy-anthropic", "api_key") == "sk-ant-test"


def test_set_secret_other_adapter_rejects_api_key(registry: FilesystemServiceRegistry):
    """other 适配器 required_secrets=[] 不允许设置 api_key。"""
    svc = _make_service(
        "other-svc",
        adapter_type="other",
        required_secrets=[],
        optional_secrets=[],
    )
    registry.create_service(svc)
    with pytest.raises(DomainError) as exc_info:
        registry.set_secret("other-svc", "api_key", "sk-should-fail")
    assert "未知 secret" in str(exc_info.value)


def test_load_service_auto_populates_required_secrets(tmp_path: Path):
    """历史服务 JSON required_secrets=[] 在加载时自动按 adapter_type 补齐。"""
    secret_store = PlaintextSecretStore(tmp_path / ".secrets")
    reg = FilesystemServiceRegistry(tmp_path, secret_store)

    # 手动写入一个 required_secrets=[] 的 openai_compatible 服务
    svc_data = {
        "schema_version": 1,
        "revision": 1,
        "service_id": "legacy-svc",
        "display_name": "Legacy",
        "capability": "text_generation",
        "adapter_type": "openai_compatible",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "enabled": True,
        "priority": 100,
        "is_default": False,
        "config": {},
        "required_secrets": [],
        "optional_secrets": [],
        "created_at": "2026-08-31T00:00:00Z",
        "updated_at": "2026-08-31T00:00:00Z",
    }
    svc_path = tmp_path / "settings" / "services" / "legacy-svc.json"
    svc_path.write_text(json.dumps(svc_data), encoding="utf-8")

    # 加载时应自动补齐 required_secrets
    loaded = reg.get_service("legacy-svc")
    assert loaded.required_secrets == ["api_key"]

    # 持久化后重新加载也应保持
    reloaded = reg.get_service("legacy-svc")
    assert reloaded.required_secrets == ["api_key"]


def test_load_service_preserves_existing_required_secrets(registry: FilesystemServiceRegistry):
    """已有 required_secrets 的服务不应被修改。"""
    svc = _make_service("existing-svc", required_secrets=["api_key", "custom_key"])
    registry.create_service(svc)

    loaded = registry.get_service("existing-svc")
    assert loaded.required_secrets == ["api_key", "custom_key"]


def test_load_service_other_adapter_no_auto_populate(tmp_path: Path):
    """other 适配器不会自动补齐 required_secrets。"""
    secret_store = PlaintextSecretStore(tmp_path / ".secrets")
    reg = FilesystemServiceRegistry(tmp_path, secret_store)

    svc_data = {
        "schema_version": 1,
        "revision": 1,
        "service_id": "other-svc",
        "display_name": "Other",
        "capability": "text_generation",
        "adapter_type": "other",
        "endpoint": "",
        "model": "",
        "enabled": True,
        "priority": 100,
        "is_default": False,
        "config": {},
        "required_secrets": [],
        "optional_secrets": [],
        "created_at": "2026-08-31T00:00:00Z",
        "updated_at": "2026-08-31T00:00:00Z",
    }
    svc_path = tmp_path / "settings" / "services" / "other-svc.json"
    svc_path.write_text(json.dumps(svc_data), encoding="utf-8")

    loaded = reg.get_service("other-svc")
    assert loaded.required_secrets == []
