"""测试 Mountain Asset API。"""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
from csboard.domain.style_template import StyleTemplate
from webapp.mountain_asset_api import mountain_asset_router


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def client(data_dir: Path) -> TestClient:
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(mountain_asset_router(data_dir))
    return TestClient(app)


@pytest.fixture
def repo(data_dir: Path) -> FilesystemAssetRepository:
    return FilesystemAssetRepository(data_dir)


class TestListStyles:
    """测试 GET /api/v1/assets/styles。"""

    def test_empty_list(self, client: TestClient):
        resp = client.get("/api/v1/assets/styles")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_with_data(self, client: TestClient, repo: FilesystemAssetRepository):
        repo.save_style_template(StyleTemplate(
            template_id="t1", revision=1, name="A", kind="custom", prompt_text="a",
        ))
        repo.save_style_template(StyleTemplate(
            template_id="t2", revision=1, name="B", kind="preset", prompt_text="b",
        ))
        resp = client.get("/api/v1/assets/styles")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_filter_by_kind(self, client: TestClient, repo: FilesystemAssetRepository):
        repo.save_style_template(StyleTemplate(
            template_id="t1", revision=1, name="A", kind="custom", prompt_text="a",
        ))
        repo.save_style_template(StyleTemplate(
            template_id="t2", revision=1, name="B", kind="preset", prompt_text="b",
        ))
        resp = client.get("/api/v1/assets/styles?kind=preset")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestGetStyle:
    """测试 GET /api/v1/assets/styles/{template_id}。"""

    def test_found(self, client: TestClient, repo: FilesystemAssetRepository):
        repo.save_style_template(StyleTemplate(
            template_id="t1", revision=1, name="A", kind="custom", prompt_text="a",
        ))
        resp = client.get("/api/v1/assets/styles/t1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "A"

    def test_not_found(self, client: TestClient):
        resp = client.get("/api/v1/assets/styles/nonexistent")
        assert resp.status_code == 404


class TestCreateStyle:
    """测试 POST /api/v1/assets/styles。"""

    def test_create_custom(self, client: TestClient):
        resp = client.post("/api/v1/assets/styles", data={
            "name": "测试风格",
            "prompt_text": "测试配方",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "测试风格"
        assert data["kind"] == "custom"

    def test_create_from_preset(self, client: TestClient, repo: FilesystemAssetRepository):
        repo.save_style_template(StyleTemplate(
            template_id="seed-001", revision=1, name="极简粗线简笔白板风",
            kind="preset", prompt_text="暖白色纯净背景...",
        ))
        resp = client.post("/api/v1/assets/styles", data={
            "name": "我的风格",
            "prompt_text": "",
            "copy_from": "seed-001",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["kind"] == "custom"
        assert data["prompt_text"] == "暖白色纯净背景..."


class TestUpdateStyle:
    """测试 PATCH /api/v1/assets/styles/{template_id}。"""

    def test_update_custom(self, client: TestClient, repo: FilesystemAssetRepository):
        repo.save_style_template(StyleTemplate(
            template_id="t1", revision=1, name="A", kind="custom", prompt_text="a",
        ))
        resp = client.patch("/api/v1/assets/styles/t1", data={"name": "B"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "B"

    def test_update_preset_forbidden(self, client: TestClient, repo: FilesystemAssetRepository):
        repo.save_style_template(StyleTemplate(
            template_id="t1", revision=1, name="A", kind="preset", prompt_text="a",
        ))
        resp = client.patch("/api/v1/assets/styles/t1", data={"name": "B"})
        assert resp.status_code == 422

    def test_update_not_found(self, client: TestClient):
        resp = client.patch("/api/v1/assets/styles/nonexistent", data={"name": "B"})
        assert resp.status_code == 404


class TestDeactivateStyle:
    """测试 DELETE /api/v1/assets/styles/{template_id}。"""

    def test_deactivate_custom(self, client: TestClient, repo: FilesystemAssetRepository):
        repo.save_style_template(StyleTemplate(
            template_id="t1", revision=1, name="A", kind="custom", prompt_text="a",
        ))
        resp = client.delete("/api/v1/assets/styles/t1")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_deactivate_preset_forbidden(self, client: TestClient, repo: FilesystemAssetRepository):
        repo.save_style_template(StyleTemplate(
            template_id="t1", revision=1, name="A", kind="preset", prompt_text="a",
        ))
        resp = client.delete("/api/v1/assets/styles/t1")
        assert resp.status_code == 422


class TestUploadAsset:
    """测试 POST /api/v1/assets/upload。"""

    def test_upload(self, client: TestClient):
        resp = client.post("/api/v1/assets/upload", files={
            "file": ("test.txt", b"hello world", "text/plain"),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["size_bytes"] == 11

    def test_upload_empty(self, client: TestClient):
        resp = client.post("/api/v1/assets/upload", files={
            "file": ("test.txt", b"", "text/plain"),
        })
        assert resp.status_code == 422
