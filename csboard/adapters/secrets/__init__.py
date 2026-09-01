"""Secret 存储适配器。"""

from .secret_store import (
    FileSecretStore,
    PlaintextSecretStore,
    SecretStoreProtocol,
    create_secret_store,
    mask_secret,
)

__all__ = [
    "FileSecretStore",
    "PlaintextSecretStore",
    "SecretStoreProtocol",
    "create_secret_store",
    "mask_secret",
]
