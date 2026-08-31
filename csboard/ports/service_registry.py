"""ServiceRegistry — 服务注册表端口。"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ServiceRegistry(Protocol):
    """服务注册表接口。"""

    def list_services(self) -> list[dict[str, Any]]:
        """列出所有服务。"""
        ...

    def get_service(self, service_id: str) -> dict[str, Any]:
        """获取单个服务状态。"""
        ...

    def update_service_config(self, service_id: str, config: dict[str, Any]) -> None:
        """更新服务配置（仅白名单字段）。"""
        ...

    def set_service_secret(self, service_id: str, secret_key: str, secret_value: str) -> None:
        """设置服务 Secret。"""
        ...

    def check_health(self, service_id: str) -> dict[str, Any]:
        """检查服务健康状态。"""
        ...

    def check_all_health(self) -> dict[str, Any]:
        """检查所有服务健康状态。"""
        ...
