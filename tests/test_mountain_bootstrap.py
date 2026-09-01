from pathlib import Path

from fastapi.testclient import TestClient

from webapp.mountain_server import create_app


def test_fresh_install_has_real_service_definitions_and_preset_assets(tmp_path: Path):
    client = TestClient(create_app(tmp_path))

    services = client.get("/api/v1/services").json()
    assert services["total"] == 6
    assert all(item["service_id"] != "mock-llm" for item in services["items"])
    text_service = next(
        item for item in services["items"]
        if item["service_id"] == "openai-compatible-text"
    )
    assert text_service["secret_status"] == {
        "configured": False,
        "required": ["api_key"],
        "missing": ["api_key"],
    }
    assert text_service["config_status"]["configured"] is False

    styles = client.get("/api/v1/assets/styles?kind=preset").json()
    assert styles["total"] == 13
    assert sum(bool(item["preview_asset_id"]) for item in styles["items"]) == 12

    preview_id = next(item["preview_asset_id"] for item in styles["items"] if item["preview_asset_id"])
    preview = client.get(f"/api/v1/assets/blobs/{preview_id}")
    assert preview.status_code == 200
    assert preview.content


def test_bootstrap_is_idempotent(tmp_path: Path):
    first = TestClient(create_app(tmp_path))
    assert first.get("/api/v1/assets/styles?kind=preset").json()["total"] == 13

    second = TestClient(create_app(tmp_path))
    assert second.get("/api/v1/services").json()["total"] == 6
    assert second.get("/api/v1/assets/styles?kind=preset").json()["total"] == 13
