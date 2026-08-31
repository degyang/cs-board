"""mountain_asset_api 结构化测试。"""

from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient

from webapp.mountain_server import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(tmp_path)
    return TestClient(app)


def test_list_styles(client: TestClient):
    response = client.get("/api/v1/assets/styles")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "next_cursor" in data


def test_create_style(client: TestClient):
    payload = {
        "name": "手绘涂鸦风",
        "kind": "custom",
        "prompt_text": "简笔涂鸦白板风",
        "engine": "whiteboard",
        "tags": ["doodle"],
    }
    response = client.post("/api/v1/assets/styles", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "custom"
    assert data["name"] == "手绘涂鸦风"
    assert data["status"] == "active"


def test_create_style_missing_name(client: TestClient):
    response = client.post("/api/v1/assets/styles", json={"prompt_text": "x"})
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_create_style_invalid_tags(client: TestClient):
    payload = {
        "name": "test",
        "prompt_text": "x",
        "tags": "not-a-list",
    }
    response = client.post("/api/v1/assets/styles", json=payload)
    assert response.status_code == 400


def test_get_style(client: TestClient):
    payload = {
        "name": "test",
        "kind": "custom",
        "prompt_text": "x",
    }
    create_resp = client.post("/api/v1/assets/styles", json=payload)
    style_id = create_resp.json()["style_id"]
    response = client.get(f"/api/v1/assets/styles/{style_id}")
    assert response.status_code == 200
    assert response.json()["style_id"] == style_id


def test_patch_style(client: TestClient):
    payload = {
        "name": "old",
        "kind": "custom",
        "prompt_text": "x",
    }
    create_resp = client.post("/api/v1/assets/styles", json=payload)
    style_id = create_resp.json()["style_id"]
    response = client.patch(f"/api/v1/assets/styles/{style_id}", json={"name": "new"})
    assert response.status_code == 200
    assert response.json()["name"] == "new"


def test_delete_style(client: TestClient):
    payload = {
        "name": "test",
        "kind": "custom",
        "prompt_text": "x",
    }
    create_resp = client.post("/api/v1/assets/styles", json=payload)
    style_id = create_resp.json()["style_id"]
    response = client.delete(f"/api/v1/assets/styles/{style_id}")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_deactivate_style(client: TestClient):
    payload = {
        "name": "test",
        "kind": "custom",
        "prompt_text": "x",
    }
    create_resp = client.post("/api/v1/assets/styles", json=payload)
    style_id = create_resp.json()["style_id"]
    response = client.post(f"/api/v1/assets/styles/{style_id}/deactivate")
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"


def test_activate_style(client: TestClient):
    payload = {
        "name": "test",
        "kind": "custom",
        "prompt_text": "x",
    }
    create_resp = client.post("/api/v1/assets/styles", json=payload)
    style_id = create_resp.json()["style_id"]
    client.post(f"/api/v1/assets/styles/{style_id}/deactivate")
    response = client.post(f"/api/v1/assets/styles/{style_id}/activate")
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_copy_preset(client: TestClient):
    """从 preset 复制创建 custom 风格。"""
    from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository

    repo = FilesystemAssetRepository(client.app.state.data_dir)
    # Write preset directly to styles.json
    styles = repo._load_styles()
    styles.append({
        "style_id": "seed-001", "revision": 1, "name": "极简粗线简笔白板风", "kind": "preset",
        "prompt_text": "...", "engine": "whiteboard", "tags": [], "status": "active",
        "created_at": "2026-08-31T00:00:00Z", "updated_at": "2026-08-31T00:00:00Z",
    })
    repo._save_styles(styles)

    response = client.post("/api/v1/assets/styles/seed-001/copy")
    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "custom"
    assert data["name"] == "极简粗线简笔白板风"
    assert data["style_id"] != "seed-001"


def test_upload_and_metadata(client: TestClient):
    audio_bytes = b"\x00" * 2048
    response = client.post(
        "/api/v1/assets/uploads",
        files={"file": ("t.mp3", audio_bytes, "audio/mpeg")},
    )
    assert response.status_code == 200
    asset_id = response.json()["asset_id"]

    blob = client.get(f"/api/v1/assets/blobs/{asset_id}")
    assert blob.status_code == 200
    assert len(blob.content) == 2048


def test_upload_missing_file(client: TestClient):
    response = client.post("/api/v1/assets/uploads")
    assert response.status_code in (400, 422)


def test_upload_path_traversal(client: TestClient):
    response = client.post(
        "/api/v1/assets/uploads",
        files={"file": ("../../../etc/passwd", b"bad", "text/plain")},
    )
    assert response.status_code == 400


def test_create_voice(client: TestClient):
    payload = {
        "name": "旁白",
        "duration_ms": 10000,
        "sample_rate": 44100,
        "channels": 1,
        "format": "wav",
    }
    response = client.post("/api/v1/assets/voices", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "旁白"
    assert data["is_active"] is True


def test_list_voices(client: TestClient):
    response = client.get("/api/v1/assets/voices")
    assert response.status_code == 200
    assert "items" in response.json()


def test_patch_voice(client: TestClient):
    payload = {"name": "old", "duration_ms": 1000, "sample_rate": 44100, "channels": 1, "format": "wav"}
    create_resp = client.post("/api/v1/assets/voices", json=payload)
    voice_id = create_resp.json()["voice_id"]
    response = client.patch(f"/api/v1/assets/voices/{voice_id}", json={"name": "new"})
    assert response.status_code == 200
    assert response.json()["name"] == "new"


def test_delete_voice(client: TestClient):
    payload = {"name": "x", "duration_ms": 1000, "sample_rate": 44100, "channels": 1, "format": "wav"}
    create_resp = client.post("/api/v1/assets/voices", json=payload)
    voice_id = create_resp.json()["voice_id"]
    response = client.delete(f"/api/v1/assets/voices/{voice_id}")
    assert response.status_code == 200


def test_deactivate_voice(client: TestClient):
    payload = {"name": "x", "duration_ms": 1000, "sample_rate": 44100, "channels": 1, "format": "wav"}
    create_resp = client.post("/api/v1/assets/voices", json=payload)
    voice_id = create_resp.json()["voice_id"]
    response = client.post(f"/api/v1/assets/voices/{voice_id}/deactivate")
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_activate_voice(client: TestClient):
    payload = {"name": "x", "duration_ms": 1000, "sample_rate": 44100, "channels": 1, "format": "wav"}
    create_resp = client.post("/api/v1/assets/voices", json=payload)
    voice_id = create_resp.json()["voice_id"]
    client.post(f"/api/v1/assets/voices/{voice_id}/deactivate")
    response = client.post(f"/api/v1/assets/voices/{voice_id}/activate")
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_style_not_found(client: TestClient):
    response = client.get("/api/v1/assets/styles/nope")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"


def test_style_presets_readonly(client: TestClient):
    """Preset 风格的 PATCH/DELETE 应返回 400。"""
    from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository

    repo = FilesystemAssetRepository(client.app.state.data_dir)
    # Write preset directly to styles.json
    styles = repo._load_styles()
    styles.append({
        "style_id": "seed-001", "revision": 1, "name": "test", "kind": "preset",
        "prompt_text": "...", "engine": "whiteboard", "tags": [], "status": "active",
        "created_at": "2026-08-31T00:00:00Z", "updated_at": "2026-08-31T00:00:00Z",
    })
    repo._save_styles(styles)

    resp = client.patch("/api/v1/assets/styles/seed-001", json={"name": "x"})
    assert resp.status_code == 400

    resp = client.delete("/api/v1/assets/styles/seed-001")
    assert resp.status_code == 400


def test_no_project_id_in_response(client: TestClient):
    """API 响应不得包含 project_id。"""
    response = client.get("/api/v1/assets/styles")
    data = response.json()
    assert "project_id" not in data
    for item in data.get("items", []):
        assert "project_id" not in item


def test_no_paths_in_response(client: TestClient):
    """API 响应不得包含路径。"""
    payload = {"name": "test", "kind": "custom", "prompt_text": "x"}
    resp = client.post("/api/v1/assets/styles", json=payload)
    data = resp.json()
    for key in data:
        assert "path" not in key.lower() or key == "prompt_text"
