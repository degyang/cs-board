"""FilesystemAssetRepository 结构化测试。"""

from __future__ import annotations

import json

import pytest

from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
from csboard.domain.errors import NotFoundError
from csboard.domain.style_template import StyleTemplate


@pytest.fixture()
def repository(tmp_path):
    return FilesystemAssetRepository(tmp_path)


def _seed_preset(repo: FilesystemAssetRepository):
    """直接写入一个 preset 到 styles.json。"""
    styles = repo._load_styles()
    styles.append({
        "style_id": "seed-001",
        "revision": 1,
        "name": "极简粗线简笔白板风",
        "kind": "preset",
        "prompt_text": "...",
        "engine": "whiteboard",
        "tags": ["seed", "whiteboard"],
        "status": "active",
        "created_at": "2026-08-31T00:00:00Z",
        "updated_at": "2026-08-31T00:00:00Z",
    })
    repo._save_styles(styles)


def test_save_and_list(repository: FilesystemAssetRepository):
    template = StyleTemplate(
        style_id="t1", revision=1, name="A", kind="custom", prompt_text="a",
        engine="whiteboard", tags=[], status="active",
        created_at="2026-08-31T00:00:00Z", updated_at="2026-08-31T00:00:00Z",
    )
    repository.save_style_template(template)
    assert len(repository.list_style_templates()) == 1


def test_list_filters_by_kind(repository: FilesystemAssetRepository):
    # Write a custom style via save
    repository.save_style_template(StyleTemplate(
        style_id="t1", revision=1, name="A", kind="custom", prompt_text="a",
        engine="whiteboard", tags=[], status="active",
        created_at="2026-08-31T00:00:00Z", updated_at="2026-08-31T00:00:00Z",
    ))
    # Write a preset directly to file (presets cannot be saved via save_style_template)
    _seed_preset(repository)
    result = repository.list_style_templates(kind="preset")
    assert len(result) == 1
    assert result[0].kind == "preset"


def test_save_preset_forbidden(repository: FilesystemAssetRepository):
    preset = StyleTemplate(
        style_id="seed-001", revision=1, name="极简粗线简笔白板风", kind="preset",
        prompt_text="...", engine="whiteboard", tags=[], status="active",
        created_at="2026-08-31T00:00:00Z", updated_at="2026-08-31T00:00:00Z",
    )
    with pytest.raises(Exception, match="preset 风格禁止修改"):
        repository.save_style_template(preset)


def test_deactivate_custom(repository: FilesystemAssetRepository):
    template = StyleTemplate(
        style_id="t1", revision=1, name="A", kind="custom", prompt_text="a",
        engine="whiteboard", tags=[], status="active",
        created_at="2026-08-31T00:00:00Z", updated_at="2026-08-31T00:00:00Z",
    )
    repository.save_style_template(template)
    repository.deactivate_style_template("t1")
    assert repository.list_style_templates(status="active") == []
    assert repository.get_style_template("t1").status == "inactive"


def test_activate(repository: FilesystemAssetRepository):
    template = StyleTemplate(
        style_id="t1", revision=1, name="A", kind="custom", prompt_text="a",
        engine="whiteboard", tags=[], status="inactive",
        created_at="2026-08-31T00:00:00Z", updated_at="2026-08-31T00:00:00Z",
    )
    repository.save_style_template(template)
    repository.activate_style_template("t1")
    assert repository.get_style_template("t1").status == "active"


def test_get_not_found(repository: FilesystemAssetRepository):
    with pytest.raises(NotFoundError):
        repository.get_style_template("nope")
