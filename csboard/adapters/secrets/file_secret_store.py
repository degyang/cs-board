"""Fernet-encrypted file-backed SecretStore."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from csboard.runtime.secret_store import SecretStore


class FileSecretStore:
    """Encrypts secrets with Fernet and stores them in a single JSON file.

    The master key is read from the ``CSBOARD_MASTER_KEY`` environment
    variable (base-64 encoded 32-byte key).  If the variable is unset a
    new key is generated on first write and printed to stderr so the
    operator can persist it.

    Requires the ``cryptography`` package.  Falls back to
    :class:`PlaintextSecretStore` if the import fails — callers should
    check ``is_encrypted`` if the distinction matters.
    """

    def __init__(self, path: Path, master_key: bytes | None = None) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from cryptography.fernet import Fernet  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "cryptography is required for FileSecretStore. "
                "Install it with: pip install cryptography"
            )

        if master_key is None:
            env = os.environ.get("CSBOARD_MASTER_KEY")
            if env:
                master_key = base64.b64decode(env)
            else:
                master_key = Fernet.generate_key()
                import sys
                print(
                    f"[FileSecretStore] Generated master key. "
                    f"Set CSBOARD_MASTER_KEY={master_key.decode()} to persist.",
                    file=sys.stderr,
                )

        self._fernet = Fernet(master_key)
        self._data: dict[str, str] = {}
        self._load()

    # ── SecretStore protocol ─────────────────────────────────────────

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

    # ── internals ────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self._path.is_file():
            return
        raw = self._path.read_bytes()
        try:
            decrypted = self._fernet.decrypt(raw)
            self._data = json.loads(decrypted)
        except Exception:
            # Corrupted or wrong key — start empty rather than crash
            self._data = {}

    def _save(self) -> None:
        plaintext = json.dumps(self._data, ensure_ascii=False).encode()
        encrypted = self._fernet.encrypt(plaintext)
        self._path.write_bytes(encrypted)
