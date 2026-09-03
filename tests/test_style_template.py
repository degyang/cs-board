"""StyleTemplate 结构化测试。"""

from __future__ import annotations

import copy

from csboard.domain.style_template import StyleTemplate


def test_fields():
    template = StyleTemplate(
        style_id="t1",
        revision=1,
        name="A",
        kind="custom",
        prompt_text="a",
        engine="whiteboard",
        description="d",
        negative_prompt="np",
        tags=["t"],
        preview_asset_id="pa",
        status="active",
        created_at="2026-08-31T00:00:00Z",
        updated_at="2026-08-31T00:00:00Z",
    )
    assert template.style_id == "t1"
    assert template.revision == 1
    assert template.engine == "whiteboard"
    assert template.description == "d"
    assert template.negative_prompt == "np"
    assert template.tags == ["t"]
    assert template.preview_asset_id == "pa"
    assert template.status == "active"


def test_to_dict_roundtrip():
    original = StyleTemplate(
        style_id="t1",
        revision=1,
        name="A",
        kind="custom",
        prompt_text="a",
        engine="whiteboard",
        tags=["x", "y"],
        status="active",
        created_at="2026-08-31T00:00:00Z",
        updated_at="2026-08-31T00:00:00Z",
    )
    restored = StyleTemplate.from_dict(original.to_dict())
    assert restored.style_id == original.style_id
    assert restored.revision == original.revision
    assert restored.name == original.name
    assert restored.kind == original.kind
    assert restored.prompt_text == original.prompt_text
    assert restored.engine == original.engine
    assert restored.tags == original.tags
    assert restored.status == original.status
    assert restored.created_at == original.created_at


def test_config_is_stable_object_and_old_data_defaults_to_empty_object():
    assert StyleTemplate.from_dict({"style_id": "old", "revision": 1, "name": "old", "kind": "custom", "prompt_text": "x"}).config == {}
    assert StyleTemplate.from_dict({"style_id": "new", "revision": 1, "name": "new", "kind": "custom", "prompt_text": "x", "config": {"palette": "warm"}}).to_dict()["config"] == {"palette": "warm"}


def test_copy_to_custom():
    preset = StyleTemplate(
        style_id="seed-001",
        revision=1,
        name="极简粗线简笔白板风",
        kind="preset",
        prompt_text="...",
        engine="whiteboard",
        tags=["seed", "whiteboard"],
        status="active",
        created_at="2026-08-31T00:00:00Z",
        updated_at="2026-08-31T00:00:00Z",
    )
    custom = preset.copy_to_custom("custom-001", "2026-08-31T01:00:00Z")
    assert custom.kind == "custom"
    assert custom.style_id == "custom-001"
    assert custom.name == preset.name
    assert custom.prompt_text == preset.prompt_text
    assert custom.engine == preset.engine
    assert custom.status == "active"
    assert custom.created_at == "2026-08-31T01:00:00Z"
    assert custom.updated_at == "2026-08-31T01:00:00Z"
    assert preset.kind == "preset"
    assert preset.style_id == "seed-001"


def test_from_dict_backward_compat_template_id():
    """from_dict 应兼容旧的 template_id 字段。"""
    data = {
        "template_id": "t1",
        "revision": 1,
        "name": "A",
        "kind": "custom",
        "prompt_text": "a",
    }
    template = StyleTemplate.from_dict(data)
    assert template.style_id == "t1"


def test_soft_delete():
    t = StyleTemplate(
        style_id="t1",
        revision=1,
        name="A",
        kind="custom",
        prompt_text="a",
        engine="whiteboard",
        status="active",
        created_at="2026-08-31T00:00:00Z",
        updated_at="2026-08-31T00:00:00Z",
    )
    assert t.status == "active"
    t.status = "inactive"
    assert t.status == "inactive"
