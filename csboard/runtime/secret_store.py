"""SecretStore protocol — abstract key/value secret management."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretStore(Protocol):
    """Read/write/delete named secrets.

    Implementations must never log, serialize into artifacts, or expose
    values through the project/run view layer.
    """

    def get(self, key: str) -> str | None:
        """Return the secret value, or *None* if not set."""
        ...

    def set(self, key: str, value: str) -> None:
        """Persist or overwrite a secret."""
        ...

    def delete(self, key: str) -> None:
        """Remove a secret.  No error if it doesn't exist."""
        ...

    def list_keys(self) -> list[str]:
        """Return all stored key names (values are NOT returned)."""
        ...
