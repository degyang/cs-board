"""Root conftest — 测试基础设施。

CSBOARD_ALLOW_PLAINTEXT_SECRETS 不再全局设置。
默认使用加密 SecretStore（cryptography 已安装）。
需要明文模式的测试使用 allow_plaintext_secret_store fixture。
"""

import os
import pytest


@pytest.fixture
def allow_plaintext_secret_store(monkeypatch):
    """Scoped fixture：临时启用明文 SecretStore。"""
    monkeypatch.setenv("CSBOARD_ALLOW_PLAINTEXT_SECRETS", "1")
    yield
    monkeypatch.delenv("CSBOARD_ALLOW_PLAINTEXT_SECRETS", raising=False)
