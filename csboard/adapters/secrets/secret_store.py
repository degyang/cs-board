"""SecretStore — 安全存储敏感配置。

支持 Fernet 加密（需要 cryptography 包）或明文降级。
不将 secret 写入 request.json、日志、诊断包或 API 响应。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class SecretStoreProtocol(Protocol):
    """SecretStore 协议。"""

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...
    def delete(self, key: str) -> None: ...
    def list_keys(self) -> list[str]: ...


class PlaintextSecretStore:
    """明文 JSON 存储（不安全，仅用于测试或 cryptography 不可用时的降级）。"""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, str] = {}
        self._load()

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._save()

    def list_keys(self) -> list[str]:
        return sorted(self._data.keys())

    def has(self, key: str) -> bool:
        return key in self._data

    def _load(self) -> None:
        if not self._path.is_file():
            return
        try:
            self._data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._data = {}

    def _save(self) -> None:
        temporary = self._path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self._path)
        try:
            import os
            os.chmod(self._path, 0o600)
        except (OSError, AttributeError):
            pass


class FileSecretStore:
    """Fernet 加密存储（需要 cryptography 包）。"""

    def __init__(self, path: Path, master_key: bytes | None = None) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from cryptography.fernet import Fernet
        except ImportError:
            raise ImportError(
                "cryptography is required for FileSecretStore. "
                "Install it with: pip install cryptography"
            )

        if master_key is None:
            import os
            env = os.environ.get("CSBOARD_MASTER_KEY")
            if env:
                master_key = env.encode("ascii")
            else:
                key_path = self._path.parent / "master.key"
                if key_path.is_file():
                    master_key = key_path.read_bytes().strip()
                else:
                    master_key = Fernet.generate_key()
                    key_path.write_bytes(master_key)
                    try:
                        os.chmod(key_path, 0o600)
                    except (OSError, AttributeError):
                        pass

        self._fernet = Fernet(master_key)
        self._data: dict[str, str] = {}
        self._load()

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value
        self._save()

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._save()

    def list_keys(self) -> list[str]:
        return sorted(self._data.keys())

    def has(self, key: str) -> bool:
        return key in self._data

    def _load(self) -> None:
        if not self._path.is_file():
            return
        raw = self._path.read_bytes()
        try:
            decrypted = self._fernet.decrypt(raw)
            self._data = json.loads(decrypted)
        except Exception:
            self._data = {}

    def _save(self) -> None:
        plaintext = json.dumps(self._data, ensure_ascii=False).encode()
        encrypted = self._fernet.encrypt(plaintext)
        self._path.write_bytes(encrypted)
        try:
            import os
            os.chmod(self._path, 0o600)
        except (OSError, AttributeError):
            pass


def create_secret_store(data_dir: Path, encrypted: bool = True) -> tuple[SecretStoreProtocol, bool]:
    """创建 SecretStore 实例。

    Args:
        data_dir: 数据目录
        encrypted: 是否使用加密存储。默认 True 要求加密，不可用时 raise。

    Returns:
        (store, is_encrypted) 元组

    Raises:
        ImportError: encrypted=True 但 cryptography 不可用（fail closed）。
    """
    secrets_dir = data_dir / ".secrets"

    if encrypted:
        store = FileSecretStore(secrets_dir / "secrets.enc")
        return store, True

    # 显式明文模式
    store = PlaintextSecretStore(secrets_dir / "secrets.json")
    return store, False


def mask_secret(value: str | None, visible_chars: int = 4) -> str:
    """掩码 secret 值，只显示首尾字符。"""
    if not value:
        return ""
    if len(value) <= visible_chars * 2:
        return "••••"
    return f"{value[:visible_chars]}••••{value[-visible_chars:]}"
