from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from csboard.adapters.secrets.plaintext_secret_store import PlaintextSecretStore
from csboard.runtime.secret_store import SecretStore


class PlaintextSecretStoreTest(unittest.TestCase):
    """Test the PlaintextSecretStore implementation."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.store = PlaintextSecretStore(self.root / "secrets.json")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_get_returns_none_for_missing(self) -> None:
        self.assertIsNone(self.store.get("nonexistent"))

    def test_set_and_get(self) -> None:
        self.store.set("api_key", "sk-abc123")
        self.assertEqual(self.store.get("api_key"), "sk-abc123")

    def test_set_overwrites(self) -> None:
        self.store.set("key", "v1")
        self.store.set("key", "v2")
        self.assertEqual(self.store.get("key"), "v2")

    def test_delete(self) -> None:
        self.store.set("key", "value")
        self.store.delete("key")
        self.assertIsNone(self.store.get("key"))

    def test_delete_nonexistent_is_noop(self) -> None:
        self.store.delete("nonexistent")  # should not raise

    def test_list_keys_sorted(self) -> None:
        self.store.set("z_key", "1")
        self.store.set("a_key", "2")
        self.store.set("m_key", "3")
        self.assertEqual(self.store.list_keys(), ["a_key", "m_key", "z_key"])

    def test_list_keys_empty(self) -> None:
        self.assertEqual(self.store.list_keys(), [])

    def test_persistence_across_instances(self) -> None:
        path = self.root / "secrets.json"
        store1 = PlaintextSecretStore(path)
        store1.set("persisted", "yes")

        store2 = PlaintextSecretStore(path)
        self.assertEqual(store2.get("persisted"), "yes")

    def test_implements_protocol(self) -> None:
        self.assertIsInstance(self.store, SecretStore)


class FileSecretStoreTest(unittest.TestCase):
    """Test FileSecretStore if cryptography is available."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        try:
            from cryptography.fernet import Fernet
            from csboard.adapters.secrets.file_secret_store import FileSecretStore
            self.key = Fernet.generate_key()
            self.store = FileSecretStore(self.root / "secrets.enc", master_key=self.key)
            self.available = True
        except ImportError:
            self.available = False

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_set_and_get(self) -> None:
        if not self.available:
            self.skipTest("cryptography not installed")
        self.store.set("api_key", "sk-secret")
        self.assertEqual(self.store.get("api_key"), "sk-secret")

    def test_persistence_across_instances(self) -> None:
        if not self.available:
            self.skipTest("cryptography not installed")
        path = self.root / "secrets.enc"
        store1 = FileSecretStore(path, master_key=self.key)
        store1.set("persisted", "encrypted_value")

        store2 = FileSecretStore(path, master_key=self.key)
        self.assertEqual(store2.get("persisted"), "encrypted_value")

    def test_wrong_key_returns_empty(self) -> None:
        if not self.available:
            self.skipTest("cryptography not installed")
        from cryptography.fernet import Fernet
        from csboard.adapters.secrets.file_secret_store import FileSecretStore

        path = self.root / "secrets.enc"
        store1 = FileSecretStore(path, master_key=self.key)
        store1.set("key", "value")

        wrong_key = Fernet.generate_key()
        store2 = FileSecretStore(path, master_key=wrong_key)
        # With wrong key, data should be empty (not crash)
        self.assertIsNone(store2.get("key"))

    def test_implements_protocol(self) -> None:
        if not self.available:
            self.skipTest("cryptography not installed")
        self.assertIsInstance(self.store, SecretStore)


if __name__ == "__main__":
    unittest.main()
