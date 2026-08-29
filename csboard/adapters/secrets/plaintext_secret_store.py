"""Plaintext file-backed SecretStore — suitable for local dev and testing."""

from __future__ import annotations

import json
from pathlib import Path

from csboard.runtime.secret_store import SecretStore


class PlaintextSecretStore:
    """Stores secrets as a plain JSON file on disk.

    **Not for production** — values are unencrypted.  Use
    :class:`FileSecretStore` (Fernet-encrypted) or a system keychain
    adapter for real deployments.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
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
        if self._path.is_file():
            self._data = json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
