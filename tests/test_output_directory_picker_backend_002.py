from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from csboard.adapters.filesystem import FilesystemTaskRepository
from csboard.domain.errors import DomainError
from webapp.mountain_server import create_app


@pytest.fixture()
def directory_fixture(tmp_path: Path):
    (tmp_path / "projects" / "nested").mkdir(parents=True)
    (tmp_path / "empty").mkdir()
    (tmp_path / "secret.txt").write_text("must not be returned", encoding="utf-8")
    client = TestClient(create_app(tmp_path))
    return tmp_path, client


def assert_error(response, code: str) -> None:
    assert response.status_code in {400, 404}
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert "message" in body["error"]
    assert "retryable" in body["error"]
    assert "unavailable" in body["error"]
    assert "details" in body["error"]


def test_root_nested_and_empty_return_relative_directories_only(directory_fixture) -> None:
    root, client = directory_fixture
    response = client.get("/api/v1/directories")
    assert response.status_code == 200
    assert response.json()["path"] == "."
    assert {item["path"] for item in response.json()["directories"]} >= {"empty", "projects"}

    nested = client.get("/api/v1/directories", params={"path": "projects"})
    assert nested.status_code == 200
    assert nested.json() == {"path": "projects", "directories": [{"name": "nested", "path": "projects/nested"}]}
    assert client.get("/api/v1/directories", params={"path": "empty"}).json() == {"path": "empty", "directories": []}
    assert "secret.txt" not in nested.text
    assert str(root) not in nested.text


@pytest.mark.parametrize("path", ["missing", "projects/missing", "../outside", "projects/../../outside", "/tmp", "//tmp"])
def test_invalid_not_found_and_traversal_paths_use_error_contract(directory_fixture, path: str) -> None:
    _, client = directory_fixture
    response = client.get("/api/v1/directories", params={"path": path})
    assert_error(response, "NOT_FOUND" if path in {"missing", "projects/missing"} else "DIRECTORY_FORBIDDEN")


def test_non_directory_is_rejected(directory_fixture) -> None:
    _, client = directory_fixture
    assert_error(client.get("/api/v1/directories", params={"path": "secret.txt"}), "DIRECTORY_NOT_DIRECTORY")


def test_symlink_escape_is_rejected_and_not_listed(directory_fixture, tmp_path: Path) -> None:
    root, client = directory_fixture
    outside = tmp_path.parent / "outside-directory-picker-002"
    outside.mkdir()
    (outside / "outside-secret").write_text("secret", encoding="utf-8")
    link = root / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink unavailable")
    assert "escape" not in client.get("/api/v1/directories").text
    assert_error(client.get("/api/v1/directories", params={"path": "escape"}), "DIRECTORY_FORBIDDEN")


def test_read_error_uses_error_contract_without_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "child").mkdir()
    before = sorted(item.name for item in root.iterdir())
    repo = FilesystemTaskRepository(root)

    def fail(_self):
        raise PermissionError("injected")

    monkeypatch.setattr(Path, "iterdir", fail)
    with pytest.raises(DomainError) as error:
        repo.browse_project_directory()
    assert error.value.code == "DIRECTORY_READ_ERROR"
    assert before == ["child"]


def test_api_read_error_uses_shared_error_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FilesystemTaskRepository(tmp_path)
    client = TestClient(create_app(tmp_path, repository=repo))
    monkeypatch.setattr(repo, "browse_project_directory", lambda _path=None: (_ for _ in ()).throw(DomainError("DIRECTORY_READ_ERROR", "目录无法读取")))
    assert_error(client.get("/api/v1/directories"), "DIRECTORY_READ_ERROR")
