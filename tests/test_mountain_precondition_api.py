"""Read-only Precondition catalog API tests."""

from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient

from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
from csboard.domain.errors import NotFoundError
from webapp.mountain_server import create_app


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(tmp_path))


def test_precondition_catalog_exposes_two_kinds_and_safe_dto(client: TestClient):
    response = client.get("/api/v1/assets/preconditions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2 and data["next_cursor"] is None
    by_kind = {item["kind"]: item for item in data["items"]}
    assert set(by_kind) == {"visual-explainer", "renderer-hand"}
    assert by_kind["visual-explainer"]["applies_to"] == ["storyboard", "illustration"]
    assert by_kind["renderer-hand"]["applies_to"] == ["whiteboard"]
    for item in data["items"]:
        assert item["revision"] == 1
        assert item["status"] == "active" and item["enabled"] is True
        assert item["engine_compatibility"] == ["whiteboard"]
        assert item["preview_asset_id"]
        assert all("path" not in key.lower() for key in item)
        assert "style" not in item and "characters" not in item


def test_precondition_detail_is_stable_and_persisted(client: TestClient):
    listed = client.get("/api/v1/assets/preconditions").json()["items"]
    item = listed[0]
    response = client.get(f"/api/v1/assets/preconditions/{item['precondition_id']}")
    assert response.status_code == 200 and response.json() == item
    path = client.app.state.data_dir / "assets" / "preconditions" / "preconditions.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert next(value for value in saved if value["precondition_id"] == item["precondition_id"])["revision"] == 1


def test_precondition_not_found_and_empty_repository(tmp_path):
    repository = FilesystemAssetRepository(tmp_path)
    assert repository.list_preconditions() == []
    with pytest.raises(NotFoundError):
        repository.get_precondition("missing")
    client = TestClient(create_app(tmp_path))
    response = client.get("/api/v1/assets/preconditions/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
