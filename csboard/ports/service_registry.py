"""ServiceRegistryPort — 服务注册表端口。

运行时不依赖 PROVIDER_PROFILES。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from csboard.domain.service_definition import ServiceDefinition


@runtime_checkable
class ServiceRegistryPort(Protocol):
    """服务注册表接口。"""

    def list_services(self, capability: str | None = None, enabled: bool | None = None) -> list[ServiceDefinition]:
        """列出服务。"""
        ...

    def get_service(self, service_id: str) -> ServiceDefinition:
        """获取单个服务。不存在时抛出 NotFoundError。"""
        ...

    def create_service(self, service: ServiceDefinition) -> ServiceDefinition:
        """创建服务。"""
        ...

    def update_service(self, service_id: str, updates: dict[str, Any]) -> ServiceDefinition:
        """更新服务。"""
        ...

    def delete_service(self, service_id: str) -> None:
        """删除服务。被引用时抛出 CONFLICT。"""
        ...

    def activate_service(self, service_id: str) -> ServiceDefinition:
        """启用服务。"""
        ...

    def deactivate_service(self, service_id: str) -> ServiceDefinition:
        """停用服务。"""
        ...

    def set_default(self, service_id: str) -> ServiceDefinition:
        """设置默认服务（同一 capability 唯一）。"""
        ...

    def get_default(self, capability: str) -> ServiceDefinition | None:
        """获取指定 capability 的默认服务。"""
        ...

    def probe_service(self, service_id: str) -> dict[str, Any]:
        """探测服务可用性。"""
        ...

    def list_secrets(self, service_id: str) -> list[dict[str, Any]]:
        """列出服务 secret 键名（不含值）。"""
        ...

    def set_secret(self, service_id: str, secret_key: str, secret_value: str) -> None:
        """设置服务 secret。"""
        ...

    def delete_secret(self, service_id: str, secret_key: str) -> None:
        """删除服务 secret。"""
        ...
