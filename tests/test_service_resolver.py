"""ServiceResolver 测试。

覆盖：
- 按 capability 选择服务
- is_default 优先
- priority 排序
- disabled 排除
- 缺少 capability 时抛出 CAPABILITY_NOT_AVAILABLE
- stage → capability 映射
- 错误包含 capability，不含 Secret
"""

from __future__ import annotations

from pathlib import Path

import pytest

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.adapters.secrets.secret_store import PlaintextSecretStore
from csboard.application.service_resolver import ServiceResolver, STAGE_CAPABILITY_MAP
from csboard.domain.errors import DomainError
from csboard.domain.service_definition import ServiceDefinition


@pytest.fixture()
def resolver(tmp_path: Path) -> ServiceResolver:
    secret_store = PlaintextSecretStore(tmp_path / ".secrets")
    registry = FilesystemServiceRegistry(tmp_path, secret_store)
    return ServiceResolver(registry)


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


def test_resolve_default_service(resolver: ServiceResolver):
    """默认服务被优先选择。"""
    resolver._registry.create_service(_make_service("svc-1", is_default=True))
    resolver._registry.create_service(_make_service("svc-2", priority=10))
    svc = resolver.resolve("text_generation")
    assert svc.service_id == "svc-1"


def test_resolve_priority(resolver: ServiceResolver):
    """无默认时按 priority 选择。第一个服务自动成为默认，创建后取消默认。"""
    resolver._registry.create_service(_make_service("svc-low", priority=200))
    resolver._registry.create_service(_make_service("svc-high", priority=10))
    # 取消所有默认
    for s in resolver._registry.list_services():
        if s.is_default:
            s.is_default = False
            resolver._registry._save_service(s)
    svc = resolver.resolve("text_generation")
    assert svc.service_id == "svc-high"


def test_resolve_disabled_excluded(resolver: ServiceResolver):
    """disabled 服务不会被选择。"""
    resolver._registry.create_service(_make_service("svc-1", enabled=False))
    with pytest.raises(DomainError) as exc_info:
        resolver.resolve("text_generation")
    assert exc_info.value.code == "CAPABILITY_NOT_AVAILABLE"


def test_resolve_no_capability(resolver: ServiceResolver):
    """缺少 capability 时抛出 CAPABILITY_NOT_AVAILABLE。"""
    with pytest.raises(DomainError) as exc_info:
        resolver.resolve("nonexistent_capability")
    assert exc_info.value.code == "CAPABILITY_NOT_AVAILABLE"
    assert exc_info.value.details["capability"] == "nonexistent_capability"


def test_resolve_for_stage(resolver: ServiceResolver):
    """按 stage 名称选择服务。"""
    resolver._registry.create_service(_make_service("text-1", capability="text_generation"))
    resolver._registry.create_service(_make_service("tts-1", capability="speech_synthesis"))
    resolver._registry.create_service(_make_service("img-1", capability="image_generation"))
    resolver._registry.create_service(_make_service("render-1", capability="rendering"))
    resolver._registry.create_service(_make_service("media-1", capability="media"))

    assert resolver.resolve_for_stage("generate-visual-anchors").service_id == "text-1"
    assert resolver.resolve_for_stage("clone-voice").service_id == "tts-1"
    assert resolver.resolve_for_stage("plan-storyboard").service_id == "text-1"
    assert resolver.resolve_for_stage("generate-illustrations").service_id == "img-1"
    assert resolver.resolve_for_stage("render-visuals").service_id == "render-1"
    assert resolver.resolve_for_stage("compose-video").service_id == "media-1"


def test_stage_capability_map_complete():
    """六阶段都有 capability 映射。"""
    expected_stages = {
        "generate-visual-anchors",
        "clone-voice",
        "plan-storyboard",
        "generate-illustrations",
        "render-visuals",
        "compose-video",
    }
    assert set(STAGE_CAPABILITY_MAP.keys()) == expected_stages


def test_error_excludes_secret(resolver: ServiceResolver):
    """错误不包含 Secret。resolver 只做选择，不检查 secret。"""
    # resolver.resolve 不检查 secret，它只是选择服务
    # secret 检查在 probe_service 和 create_adapter 时发生
    # 这里测试 resolve 失败时的错误不包含 secret
    with pytest.raises(DomainError) as exc_info:
        resolver.resolve("nonexistent_capability")
    error_str = str(exc_info.value.details)
    # capability 错误中不应有 secret 信息
    assert "api_key" not in error_str


def test_switch_default_affects_resolution(resolver: ServiceResolver):
    """更新默认服务后下一次 Pipeline 使用新服务。"""
    resolver._registry.create_service(_make_service("svc-1", is_default=True))
    resolver._registry.create_service(_make_service("svc-2"))
    assert resolver.resolve("text_generation").service_id == "svc-1"

    resolver._registry.set_default("svc-2")
    assert resolver.resolve("text_generation").service_id == "svc-2"
