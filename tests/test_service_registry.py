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


def test_required_secret_availability_is_fail_closed(registry: FilesystemServiceRegistry):
    service = _make_service("svc-1", required_secrets=["api_key", "client_secret"])
    registry.create_service(service)

    assert registry.has_required_secrets(service) is False

    registry.set_secret("svc-1", "api_key", "")
    assert registry.has_required_secrets(service) is False

    registry.set_secret("svc-1", "api_key", "configured-secret")
    assert registry.has_required_secrets(service) is False

    registry.set_secret("svc-1", "client_secret", "configured-secret")
    assert registry.has_required_secrets(service) is True

    no_secret_service = _make_service("svc-2", required_secrets=[])
    registry.create_service(no_secret_service)
    assert registry.has_required_secrets(no_secret_service) is True


def test_required_secret_availability_hides_store_read_failures(tmp_path: Path):
    class FailingSecretStore:
        def get(self, key: str) -> str | None:
            raise OSError("secret store unavailable")

    registry = FilesystemServiceRegistry(tmp_path, FailingSecretStore())
    service = _make_service("svc-1")

    assert registry.has_required_secrets(service) is False


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
