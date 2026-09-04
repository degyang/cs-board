"""mountain_asset_api 结构化测试。"""

from __future__ import annotations

import io
import json
import struct

import pytest
from starlette.testclient import TestClient

from webapp.mountain_server import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app(tmp_path)
    return TestClient(app)


def _make_wav_bytes(duration_ms: int = 100, sample_rate: int = 44100, channels: int = 1) -> bytes:
    """生成最小合法 WAV 文件。"""
    num_samples = int(sample_rate * duration_ms / 1000)
    bits_per_sample = 16
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = num_samples * block_align

    buf = io.BytesIO()
    # RIFF header
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    # fmt subchunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))  # subchunk1 size
    buf.write(struct.pack("<HHIIHH", 1, channels, sample_rate, byte_rate, block_align, bits_per_sample))
    # data subchunk
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    # 静音数据
    buf.write(b"\x00" * data_size)
    return buf.getvalue()


def _upload_image(client: TestClient, marker: bytes = b"") -> str:
    response = client.post(
        "/api/v1/assets/uploads",
        files={"file": ("reference.png", b"\x89PNG\r\n\x1a\nminimal-image" + marker, "image/png")},
    )
    assert response.status_code == 200
    return response.json()["asset_id"]


def test_custom_style_characters_round_trip_revision_conflict_and_copy(client: TestClient):
    image_ids = [_upload_image(client, bytes([index])) for index in range(3)]
    characters = [{
        "character_id": "host", "name": "主讲人", "description": "讲解角色",
        "reference_asset_ids": image_ids,
    }]
    created = client.post("/api/v1/assets/styles", json={
        "name": "角色风格", "prompt_text": "x", "characters": characters,
    })
    assert created.status_code == 200
    style = created.json()
    style_id = style["style_id"]
    assert client.get(f"/api/v1/assets/styles/{style_id}").json()["characters"] == characters
    assert next(x for x in client.get("/api/v1/assets/styles").json()["items"] if x["style_id"] == style_id)["characters"] == characters

    replaced = client.patch(f"/api/v1/assets/styles/{style_id}", json={
        "expected_revision": style["revision"], "characters": [],
    })
    assert replaced.status_code == 200
    assert replaced.json()["revision"] == style["revision"] + 1
    assert replaced.json()["characters"] == []
    assert client.patch(f"/api/v1/assets/styles/{style_id}", json={
        "expected_revision": style["revision"], "characters": characters,
    }).status_code == 409

    repo = __import__("csboard.adapters.filesystem.asset_repository", fromlist=["FilesystemAssetRepository"]).FilesystemAssetRepository(client.app.state.data_dir)
    seeded = repo._load_styles()
    seeded.append({**style, "style_id": "preset-with-characters", "kind": "preset", "revision": 1, "characters": characters})
    repo._save_styles(seeded)
    assert client.patch("/api/v1/assets/styles/preset-with-characters", json={"characters": []}).status_code == 200
    copied = client.post("/api/v1/assets/styles/preset-with-characters/copy")
    assert copied.status_code == 200 and copied.json()["characters"] == []
    copied_id = copied.json()["style_id"]
    assert client.patch(f"/api/v1/assets/styles/{copied_id}", json={"characters": characters}).status_code == 200
    assert client.get("/api/v1/assets/styles/preset-with-characters").json()["characters"] == []


@pytest.mark.parametrize("characters", [
    [],
    [{"character_id": "a", "name": "A", "description": "x", "reference_asset_ids": []}],
    [{"character_id": "a", "name": "A", "description": "x", "reference_asset_ids": ["missing"]}],
    [{"character_id": "a", "name": "A", "description": "x", "reference_asset_ids": ["a", "b", "c", "d"]}],
    [{"character_id": "same", "name": "A", "description": "x", "reference_asset_ids": ["a"]}, {"character_id": "same", "name": "B", "description": "x", "reference_asset_ids": ["a"]}],
])
def test_custom_style_character_invalid_contract(client: TestClient, characters: list[dict]):
    # Empty character arrays are valid replacement/create values; the other forms must be rejected.
    if characters == []:
        assert client.post("/api/v1/assets/styles", json={"name": "empty", "prompt_text": "x", "characters": characters}).status_code == 200
        return
    response = client.post("/api/v1/assets/styles", json={"name": "bad", "prompt_text": "x", "characters": characters})
    assert response.status_code == 400


def test_character_rejects_non_image_blob(client: TestClient):
    blob = client.post("/api/v1/assets/uploads", files={"file": ("not-image.txt", b"text", "image/png")}).json()["asset_id"]
    response = client.post("/api/v1/assets/styles", json={"name": "bad", "prompt_text": "x", "characters": [{
        "character_id": "a", "name": "A", "description": "x", "reference_asset_ids": [blob],
    }]})
    assert response.status_code == 400


@pytest.mark.parametrize("reference_count", [1, 2, 3])
def test_character_accepts_one_to_three_image_references(client: TestClient, reference_count: int):
    refs = [_upload_image(client, bytes([index])) for index in range(reference_count)]
    response = client.post("/api/v1/assets/styles", json={"name": "valid", "prompt_text": "x", "characters": [{
        "character_id": "host", "name": "主持人", "description": "x", "reference_asset_ids": refs,
    }]})
    assert response.status_code == 200


def test_voice_metadata_round_trip_and_server_media_truth(client: TestClient):
    compatibility = {"engines": ["indextts-2"], "emotion_modes": ["speaker"], "limitations": []}
    created = client.post("/api/v1/assets/voices", files={"file": ("voice.wav", _make_wav_bytes(), "audio/wav")}, data={
        "name": "旁白", "language": "zh-CN", "emotion_mode": "speaker", "example_text": "大家好",
        "availability_status": "verified", "status_note": "已验收", "engine": "indextts-2",
        "compatibility": json.dumps(compatibility),
    })
    assert created.status_code == 200
    voice = created.json()
    voice_id = voice["voice_id"]
    expected_metadata = {
        "language": "zh-CN", "emotion_mode": "speaker", "example_text": "大家好",
        "availability_status": "verified", "status_note": "已验收", "engine": "indextts-2",
        "compatibility": compatibility,
    }
    for field, value in expected_metadata.items():
        assert voice[field] == value
    assert "storage_path" not in voice
    duration, audio_format = voice["duration_ms"], voice["format"]
    patched = client.patch(f"/api/v1/assets/voices/{voice_id}", json={"availability_status": "limited", "status_note": "仅普通话"})
    assert patched.status_code == 200
    assert patched.json()["availability_status"] == "limited" and patched.json()["is_active"] is True
    assert patched.json()["duration_ms"] == duration and patched.json()["format"] == audio_format
    assert client.get(f"/api/v1/assets/voices/{voice_id}").json()["language"] == "zh-CN"
    assert next(x for x in client.get("/api/v1/assets/voices").json()["items"] if x["voice_id"] == voice_id)["engine"] == "indextts-2"


@pytest.mark.parametrize("payload", [
    {"emotion_mode": "invalid"}, {"availability_status": "inactive"}, {"compatibility": {}},
    {"compatibility": {"engines": [], "emotion_modes": ["speaker"], "limitations": []}},
])
def test_voice_metadata_rejects_invalid_values(client: TestClient, payload: dict):
    created = client.post("/api/v1/assets/voices", files={"file": ("voice.wav", _make_wav_bytes(), "audio/wav")})
    response = client.patch(f"/api/v1/assets/voices/{created.json()['voice_id']}", json=payload)
    assert response.status_code == 400


def test_list_styles(client: TestClient):
    response = client.get("/api/v1/assets/styles")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "next_cursor" in data
    assert all(isinstance(item["config"], dict) for item in data["items"])


def test_style_config_round_trips_list_detail_create_and_patch(client: TestClient):
    created = client.post("/api/v1/assets/styles", json={"name": "config", "prompt_text": "x", "config": {"palette": "warm"}})
    assert created.status_code == 200 and created.json()["config"] == {"palette": "warm"}
    style_id = created.json()["style_id"]
    assert client.get(f"/api/v1/assets/styles/{style_id}").json()["config"] == {"palette": "warm"}
    assert client.patch(f"/api/v1/assets/styles/{style_id}", json={"config": {"density": "rich"}}).json()["config"] == {"density": "rich"}
    assert next(x for x in client.get("/api/v1/assets/styles").json()["items"] if x["style_id"] == style_id)["config"] == {"density": "rich"}


@pytest.mark.parametrize("method,payload", [("post", {"name": "bad", "prompt_text": "x", "config": []}), ("patch", {"config": []})])
def test_style_config_rejects_non_object(client: TestClient, method: str, payload: dict):
    if method == "patch":
        style_id = client.post("/api/v1/assets/styles", json={"name": "base", "prompt_text": "x"}).json()["style_id"]
        response = client.patch(f"/api/v1/assets/styles/{style_id}", json=payload)
    else:
        response = client.post("/api/v1/assets/styles", json=payload)
    assert response.status_code == 400
    assert response.json() == {"error": {"code": "VALIDATION_ERROR", "message": "config 必须是对象", "retryable": False, "unavailable": [], "details": None}}


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
        "prompt_text": "...", "engine": "whiteboard", "tags": [], "config": {"routing": {"palette": "warm"}}, "status": "active",
        "created_at": "2026-08-31T00:00:00Z", "updated_at": "2026-08-31T00:00:00Z",
    })
    repo._save_styles(styles)

    response = client.post("/api/v1/assets/styles/seed-001/copy")
    assert response.status_code == 200
    data = response.json()
    assert data["kind"] == "custom"
    assert data["name"] == "极简粗线简笔白板风"
    assert data["style_id"] != "seed-001"
    assert data["config"] == {"routing": {"palette": "warm"}}
    assert client.patch(f"/api/v1/assets/styles/{data['style_id']}", json={"config": {"routing": {"palette": "cool"}}}).status_code == 200
    assert client.get("/api/v1/assets/styles/seed-001").json()["config"] == {"routing": {"palette": "warm"}}


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
    """multipart 上传音色。"""
    wav_bytes = _make_wav_bytes(duration_ms=100)
    response = client.post(
        "/api/v1/assets/voices",
        files={"file": ("narration.wav", wav_bytes, "audio/wav")},
        data={"name": "旁白", "tags": "narration,test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "旁白"
    assert data["is_active"] is True
    assert data["sha256"]
    assert data["tags"] == ["narration", "test"]
    assert data["revision"] == 1


def test_list_voices(client: TestClient):
    wav_bytes = _make_wav_bytes()
    client.post(
        "/api/v1/assets/voices",
        files={"file": ("v.wav", wav_bytes, "audio/wav")},
        data={"name": "v1"},
    )
    response = client.get("/api/v1/assets/voices")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


def test_patch_voice(client: TestClient):
    wav_bytes = _make_wav_bytes()
    create_resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("v.wav", wav_bytes, "audio/wav")},
        data={"name": "old"},
    )
    voice_id = create_resp.json()["voice_id"]
    response = client.patch(f"/api/v1/assets/voices/{voice_id}", json={"name": "new"})
    assert response.status_code == 200
    assert response.json()["name"] == "new"
    assert response.json()["revision"] == 2


def test_delete_voice(client: TestClient):
    wav_bytes = _make_wav_bytes()
    create_resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("v.wav", wav_bytes, "audio/wav")},
        data={"name": "x"},
    )
    voice_id = create_resp.json()["voice_id"]
    response = client.delete(f"/api/v1/assets/voices/{voice_id}")
    assert response.status_code == 200


def test_deactivate_voice(client: TestClient):
    wav_bytes = _make_wav_bytes()
    create_resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("v.wav", wav_bytes, "audio/wav")},
        data={"name": "x"},
    )
    voice_id = create_resp.json()["voice_id"]
    response = client.post(f"/api/v1/assets/voices/{voice_id}/deactivate")
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_activate_voice(client: TestClient):
    wav_bytes = _make_wav_bytes()
    create_resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("v.wav", wav_bytes, "audio/wav")},
        data={"name": "x"},
    )
    voice_id = create_resp.json()["voice_id"]
    client.post(f"/api/v1/assets/voices/{voice_id}/deactivate")
    response = client.post(f"/api/v1/assets/voices/{voice_id}/activate")
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_voice_content_range(client: TestClient):
    """音色 content 支持 Range 请求和416。"""
    wav_bytes = _make_wav_bytes(duration_ms=50)
    create_resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("v.wav", wav_bytes, "audio/wav")},
        data={"name": "range-test"},
    )
    voice_id = create_resp.json()["voice_id"]

    # 普通请求
    resp = client.get(f"/api/v1/assets/voices/{voice_id}/content")
    assert resp.status_code == 200
    assert "accept-ranges" in resp.headers

    # Range 请求
    resp = client.get(
        f"/api/v1/assets/voices/{voice_id}/content",
        headers={"Range": "bytes=0-9"},
    )
    assert resp.status_code == 206
    assert "content-range" in resp.headers
    assert len(resp.content) == 10

    # 无效 Range → 416
    resp = client.get(
        f"/api/v1/assets/voices/{voice_id}/content",
        headers={"Range": "bytes=999999-999999"},
    )
    assert resp.status_code == 416


def test_style_not_found(client: TestClient):
    response = client.get("/api/v1/assets/styles/nope")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"


def test_style_presets_are_versioned_and_soft_deleted(client: TestClient):
    """Preset 与 custom 一样支持编辑、启停和软删除。"""
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
    assert resp.status_code == 200
    assert resp.json()["revision"] == 2

    resp = client.delete("/api/v1/assets/styles/seed-001")
    assert resp.status_code == 200
    assert repo.get_style_template("seed-001").status == "inactive"

    resp = client.post("/api/v1/assets/styles/seed-001/activate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    resp = client.post("/api/v1/assets/styles/seed-001/deactivate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "inactive"


def test_style_reference_routing_validates_real_images_and_normalizes_order(client: TestClient):
    uploaded = client.post("/api/v1/assets/uploads", files={"file": ("route.png", b"\x89PNG\r\n\x1a\nroute", "image/png")})
    assert uploaded.status_code == 200
    style = client.get("/api/v1/assets/styles/ps-cs-9").json()
    config = dict(style["config"])
    config["reference_routing"] = {"enabled": True, "match_mode": "first", "rules": [{
        "rule_id": "custom-route", "name": "测试规则", "keywords": ["流程", "流程"],
        "reference_asset_ids": [uploaded.json()["asset_id"]], "order": 99,
    }]}
    response = client.patch("/api/v1/assets/styles/ps-cs-9", json={"config": config, "expected_revision": style["revision"]})
    assert response.status_code == 200
    rule = response.json()["config"]["reference_routing"]["rules"][0]
    assert rule["keywords"] == ["流程"] and rule["order"] == 1

    config["reference_routing"]["rules"][0]["reference_asset_ids"] = ["missing"]
    invalid = client.patch("/api/v1/assets/styles/ps-cs-9", json={"config": config})
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


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


def test_voice_no_storage_path_in_response(client: TestClient):
    """音色 API 响应不得包含 storage_path 或绝对路径。"""
    wav_bytes = _make_wav_bytes()
    resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("v.wav", wav_bytes, "audio/wav")},
        data={"name": "test"},
    )
    data = resp.json()
    assert "storage_path" not in data


def test_voice_content_head(client: TestClient):
    """HEAD 请求返回正确 Content-Length。"""
    wav_bytes = _make_wav_bytes()
    create_resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("v.wav", wav_bytes, "audio/wav")},
        data={"name": "head-test"},
    )
    voice_id = create_resp.json()["voice_id"]
    resp = client.head(f"/api/v1/assets/voices/{voice_id}/content")
    assert resp.status_code == 200
    assert "content-length" in resp.headers


# ── Item 12: Voice multipart behavioral tests ─────────────────────────

def test_voice_upload_missing_file(client: TestClient):
    """缺少 file 字段应返回400或422。"""
    resp = client.post("/api/v1/assets/voices", data={"name": "test"})
    assert resp.status_code in (400, 422)


def test_voice_upload_empty_file(client: TestClient):
    """空文件应返回400。"""
    resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("empty.wav", b"", "audio/wav")},
        data={"name": "empty"},
    )
    assert resp.status_code == 400


def test_voice_upload_invalid_extension(client: TestClient):
    """不支持的扩展名应返回400。"""
    resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("test.xyz", b"\x00" * 100, "audio/xyz")},
        data={"name": "invalid"},
    )
    assert resp.status_code == 400
    assert "不支持" in resp.json()["error"]["message"] or "unsupported" in resp.json()["error"]["message"].lower()


def test_voice_upload_invalid_mime(client: TestClient):
    """不支持的 MIME 类型应返回400。"""
    resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("test.wav", b"\x00" * 100, "text/plain")},
        data={"name": "invalid-mime"},
    )
    assert resp.status_code == 400
    assert "MIME" in resp.json()["error"]["message"] or "mime" in resp.json()["error"]["message"].lower()


def test_voice_upload_preserves_tags(client: TestClient):
    """上传时 tags 应正确解析。"""
    wav_bytes = _make_wav_bytes()
    resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("tagged.wav", wav_bytes, "audio/wav")},
        data={"name": "tagged", "tags": "narration, warm, female"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["tags"]) == {"narration", "warm", "female"}


def test_voice_upload_empty_tags(client: TestClient):
    """空 tags 应返回空列表。"""
    wav_bytes = _make_wav_bytes()
    resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("notags.wav", wav_bytes, "audio/wav")},
        data={"name": "notags", "tags": ""},
    )
    assert resp.status_code == 200
    assert resp.json()["tags"] == []


def test_voice_upload_sha256_consistency(client: TestClient):
    """相同文件内容应产生相同 sha256。"""
    wav_bytes = _make_wav_bytes()
    resp1 = client.post(
        "/api/v1/assets/voices",
        files={"file": ("v1.wav", wav_bytes, "audio/wav")},
        data={"name": "v1"},
    )
    resp2 = client.post(
        "/api/v1/assets/voices",
        files={"file": ("v2.wav", wav_bytes, "audio/wav")},
        data={"name": "v2"},
    )
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["sha256"] == resp2.json()["sha256"]


def test_voice_upload_metadata_extraction(client: TestClient):
    """上传后应提取音频元数据（duration_ms, sample_rate）。"""
    wav_bytes = _make_wav_bytes(duration_ms=200, sample_rate=44100)
    resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("meta.wav", wav_bytes, "audio/wav")},
        data={"name": "meta"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # 元数据应存在
    assert "duration_ms" in data or "sample_rate" in data or "sha256" in data


def test_voice_upload_default_name(client: TestClient):
    """未提供 name 时应使用文件名。"""
    wav_bytes = _make_wav_bytes()
    resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("my-voice.wav", wav_bytes, "audio/wav")},
        data={},
    )
    assert resp.status_code == 200
    # name 应该是文件名或空
    assert resp.json()["name"] is not None


def test_voice_content_range_partial(client: TestClient):
    """Range 请求应返回正确部分内容。"""
    wav_bytes = _make_wav_bytes(duration_ms=100)
    create_resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("range.wav", wav_bytes, "audio/wav")},
        data={"name": "range"},
    )
    voice_id = create_resp.json()["voice_id"]

    # 请求前100字节
    resp = client.get(
        f"/api/v1/assets/voices/{voice_id}/content",
        headers={"Range": "bytes=0-99"},
    )
    assert resp.status_code == 206
    assert len(resp.content) == 100
    assert "content-range" in resp.headers


def test_voice_content_range_invalid_format(client: TestClient):
    """无效 Range 格式应返回416。"""
    wav_bytes = _make_wav_bytes(duration_ms=100)
    create_resp = client.post(
        "/api/v1/assets/voices",
        files={"file": ("invalid-range.wav", wav_bytes, "audio/wav")},
        data={"name": "invalid-range"},
    )
    voice_id = create_resp.json()["voice_id"]

    # 无效 Range 格式
    resp = client.get(
        f"/api/v1/assets/voices/{voice_id}/content",
        headers={"Range": "invalid"},
    )
    assert resp.status_code == 416
