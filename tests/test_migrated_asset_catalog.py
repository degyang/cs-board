from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from starlette.testclient import TestClient

from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
from csboard.application.migrated_asset_catalog import seed as seed_migrated_assets
from csboard.application.preset_catalog import seed as seed_presets
from csboard.domain.errors import DomainError
from webapp.mountain_server import create_app


def test_fresh_start_installs_baseline_assets_and_playable_wav(tmp_path):
    client = TestClient(create_app(tmp_path))
    presets = client.get("/api/v1/assets/styles", params={"kind": "preset", "limit": 100}).json()
    customs = client.get("/api/v1/assets/styles", params={"kind": "custom", "limit": 100}).json()
    voices = client.get("/api/v1/assets/voices").json()

    assert presets["total"] == 13
    assert customs["total"] == 2
    assert voices["total"] == 11
    assert {item["name"] for item in customs["items"]} == {"我的科普风", "复古漫画风"}
    by_name = {item["name"]: item for item in presets["items"]}
    paper = by_name["纸感隐喻拼贴风"]["config"]["reference_routing"]
    oil = by_name["漫画墨线解释风"]["config"]["reference_routing"]
    assert paper["enabled"] is True and paper["match_mode"] == "first" and len(paper["rules"]) == 9
    assert oil["enabled"] is True and len(oil["rules"]) == 5
    assert paper["rules"][0]["keywords"] == ["流程", "系统", "自动化", "生产", "步骤", "机器", "效率"]
    assert len(paper["rules"][1]["reference_asset_ids"]) == 2
    for rule in paper["rules"] + oil["rules"]:
        for asset_id in rule["reference_asset_ids"]:
            image = client.get(f"/api/v1/assets/blobs/{asset_id}")
            assert image.status_code == 200 and image.content.startswith(b"\x89PNG")
    assert {item["voice_id"] for item in voices["items"]} == {
        "vc-01", "vc-02", "vc-03", "vc-04", "vc-08", "vc-09",
        "vc-10", "vc-11", "vc-12", "vc-13", "vc-14",
    }

    voice = next(item for item in voices["items"] if item["voice_id"] == "vc-10")
    assert voice["duration_ms"] == 2036
    assert voice["sample_rate"] == 48000
    assert voice["emotion_mode"] == "reference_audio"
    assert voice["emotion_weight"] == 0.65
    assert voice["emotion_reference_asset_id"]
    assert "storage_path" not in voice

    content = client.get("/api/v1/assets/voices/vc-10/content")
    assert content.status_code == 200
    assert content.content.startswith(b"RIFF")
    partial = client.get("/api/v1/assets/voices/vc-10/content", headers={"Range": "bytes=0-31"})
    assert partial.status_code == 206
    assert partial.content == content.content[:32]
    assert partial.headers["accept-ranges"] == "bytes"

    emotion = client.get(f"/api/v1/assets/blobs/{voice['emotion_reference_asset_id']}")
    assert emotion.status_code == 200
    assert emotion.content.startswith(b"RIFF")


def test_second_start_and_repository_rebuild_do_not_duplicate(tmp_path):
    create_app(tmp_path)
    create_app(tmp_path)
    rebuilt = FilesystemAssetRepository(tmp_path)
    assert len(rebuilt.list_style_templates(kind="preset")) == 13
    assert len(rebuilt.list_style_templates(kind="custom")) == 2
    assert len(rebuilt.list_voice_assets()) == 11
    assert rebuilt.get_voice_content("vc-14").startswith(b"RIFF")


def test_seed_migrates_old_routing_once_but_preserves_an_explicitly_cleared_list(tmp_path):
    seed_presets(tmp_path)
    repository = FilesystemAssetRepository(tmp_path)
    paper = repository.get_style_template("ps-cs-9")
    paper.config = {}
    repository.save_style_template(paper, expected_revision=paper.revision)
    seed_presets(tmp_path)
    migrated = repository.get_style_template("ps-cs-9")
    assert len(migrated.config["reference_routing"]["rules"]) == 9

    migrated.config["reference_routing"] = {"enabled": False, "match_mode": "first", "rules": []}
    repository.save_style_template(migrated, expected_revision=migrated.revision)
    seed_presets(tmp_path)
    assert repository.get_style_template("ps-cs-9").config["reference_routing"] == {
        "enabled": False, "match_mode": "first", "rules": [],
    }


def test_seed_preserves_user_changes_and_does_not_revive(tmp_path):
    client = TestClient(create_app(tmp_path))
    edited = client.patch("/api/v1/assets/styles/ps-cs-1", json={
        "name": "用户修改的预置", "expected_revision": 1,
    })
    assert edited.status_code == 200
    assert client.post("/api/v1/assets/styles/ps-cs-4/deactivate").status_code == 200
    assert client.delete("/api/v1/assets/styles/cs-1").status_code == 200
    voice = client.patch("/api/v1/assets/voices/vc-01", json={
        "name": "用户修改的音色", "expected_revision": 1,
    })
    assert voice.status_code == 200
    assert client.post("/api/v1/assets/voices/vc-02/deactivate").status_code == 200

    create_app(tmp_path)
    rebuilt = FilesystemAssetRepository(tmp_path)
    assert rebuilt.get_style_template("ps-cs-1").name == "用户修改的预置"
    assert rebuilt.get_style_template("ps-cs-4").status == "inactive"
    assert rebuilt.get_style_template("cs-1").status == "inactive"
    assert rebuilt.get_voice_asset("vc-01").name == "用户修改的音色"
    assert rebuilt.get_voice_asset("vc-02").is_active is False
    assert len(rebuilt.list_voice_assets()) == 10


def test_preset_revision_conflict_is_enforced(tmp_path):
    client = TestClient(create_app(tmp_path))
    first = client.patch("/api/v1/assets/styles/ps-cs-2", json={
        "name": "第一次修改", "expected_revision": 1,
    })
    stale = client.patch("/api/v1/assets/styles/ps-cs-2", json={
        "name": "过期修改", "expected_revision": 1,
    })
    assert first.status_code == 200
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "REVISION_CONFLICT"

    voice_first = client.patch("/api/v1/assets/voices/vc-03", json={
        "name": "第一次音色修改", "expected_revision": 1,
    })
    voice_stale = client.patch("/api/v1/assets/voices/vc-03", json={
        "name": "过期音色修改", "expected_revision": 1,
    })
    assert voice_first.status_code == 200
    assert voice_stale.status_code == 409
    assert voice_stale.json()["error"]["code"] == "REVISION_CONFLICT"


def test_api_can_create_and_manage_a_new_preset(tmp_path):
    client = TestClient(create_app(tmp_path))
    created = client.post("/api/v1/assets/styles", json={
        "kind": "preset", "name": "团队预置", "prompt_text": "团队视觉规范",
    })
    assert created.status_code == 200
    style = created.json()
    assert style["kind"] == "preset"
    edited = client.patch(f"/api/v1/assets/styles/{style['style_id']}", json={
        "description": "已版本化", "expected_revision": style["revision"],
    })
    assert edited.status_code == 200
    assert edited.json()["revision"] == 2
    assert client.delete(f"/api/v1/assets/styles/{style['style_id']}").status_code == 200


def test_concurrent_seed_is_idempotent(tmp_path):
    def install() -> None:
        seed_presets(tmp_path)
        seed_migrated_assets(tmp_path)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: install(), range(8)))

    repository = FilesystemAssetRepository(tmp_path)
    assert len(repository.list_style_templates(kind="preset")) == 13
    assert len(repository.list_style_templates(kind="custom")) == 2
    assert len(repository.list_voice_assets()) == 11


def test_oil_visual_routing_survives_fresh_seed_and_repository_rebuild(tmp_path):
    """Regression: 纸感隐喻拼贴风有路由时，漫画墨线解释风也必须有五条规则且图片可读。"""
    client = TestClient(create_app(tmp_path))
    presets = client.get("/api/v1/assets/styles", params={"kind": "preset", "limit": 100}).json()
    by_name = {item["name"]: item for item in presets["items"]}

    paper = by_name["纸感隐喻拼贴风"]["config"]["reference_routing"]
    oil = by_name["漫画墨线解释风"]["config"]["reference_routing"]

    assert paper["enabled"] is True and len(paper["rules"]) == 9
    assert oil["enabled"] is True and len(oil["rules"]) == 5
    assert oil["match_mode"] == "first"

    expected_names = {"机制对比", "机制循环", "机制流程", "角色场景", "概念解释"}
    actual_names = {rule["name"] for rule in oil["rules"]}
    assert actual_names == expected_names

    for rule in oil["rules"]:
        assert 1 <= len(rule["reference_asset_ids"]) <= 3
        for asset_id in rule["reference_asset_ids"]:
            image = client.get(f"/api/v1/assets/blobs/{asset_id}")
            assert image.status_code == 200
            assert image.content[:4] == b"\x89PNG"

    # Verify idempotent rebuild preserves routing
    create_app(tmp_path)
    rebuilt = FilesystemAssetRepository(tmp_path)
    rebuilt_oil = rebuilt.get_style_template("ps-cs-10")
    assert rebuilt_oil.config["reference_routing"]["enabled"] is True
    assert len(rebuilt_oil.config["reference_routing"]["rules"]) == 5


def test_repository_rejects_stale_concurrent_style_update(tmp_path):
    seed_presets(tmp_path)
    first = FilesystemAssetRepository(tmp_path)
    second = FilesystemAssetRepository(tmp_path)
    left = first.get_style_template("ps-cs-3")
    right = second.get_style_template("ps-cs-3")
    left.name = "winner"
    first.save_style_template(left, expected_revision=1)
    right.name = "stale"
    try:
        second.save_style_template(right, expected_revision=1)
    except DomainError as exc:
        assert exc.code == "REVISION_CONFLICT"
    else:
        raise AssertionError("stale update must conflict")
