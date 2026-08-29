"""SecretStore — 安全存储敏感配置。

不将 secret 写入 request.json、日志、诊断包或 API 响应。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SecretStore:
    """基于文件的 secret 存储。

    存储位置：{data_dir}/.secrets/secrets.json
    文件权限：仅 owner 可读写（0600）。
    """

    def __init__(self, data_dir: Path) -> None:
        self._secrets_dir = data_dir / ".secrets"
        self._secrets_file = self._secrets_dir / "secrets.json"
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """确保目录存在且权限正确。"""
        self._secrets_dir.mkdir(parents=True, exist_ok=True)
        try:
            import os
            os.chmod(self._secrets_dir, 0o700)
        except (OSError, AttributeError):
            pass  # Windows 不支持 chmod

    def _load(self) -> dict[str, str]:
        """加载 secrets。"""
        if not self._secrets_file.exists():
            return {}
        try:
            return json.loads(self._secrets_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict[str, str]) -> None:
        """保存 secrets。"""
        temporary = self._secrets_file.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self._secrets_file)
        try:
            import os
            os.chmod(self._secrets_file, 0o600)
        except (OSError, AttributeError):
            pass

    def get(self, key: str) -> str | None:
        """获取 secret 值。"""
        return self._load().get(key)

    def set(self, key: str, value: str) -> None:
        """设置 secret 值。"""
        data = self._load()
        data[key] = value
        self._save(data)

    def delete(self, key: str) -> bool:
        """删除 secret。"""
        data = self._load()
        if key not in data:
            return False
        del data[key]
        self._save(data)
        return True

    def list_keys(self) -> list[str]:
        """列出所有 secret key（不返回值）。"""
        return list(self._load().keys())

    def has(self, key: str) -> bool:
        """检查 secret 是否存在。"""
        return key in self._load()


def mask_secret(value: str | None, visible_chars: int = 4) -> str:
    """掩码 secret 值，只显示首尾字符。"""
    if not value:
        return ""
    if len(value) <= visible_chars * 2:
        return "••••"
    return f"{value[:visible_chars]}••••{value[-visible_chars:]}"
