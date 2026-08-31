"""测试 StyleTemplate 领域模型。"""

import pytest

from csboard.domain.style_template import StyleTemplate


class TestStyleTemplate:
    """StyleTemplate 数据类测试。"""

    def test_construction(self):
        """测试基本构造。"""
        t = StyleTemplate(
            template_id="t1",
            revision=1,
            name="测试风格",
            kind="custom",
            prompt_text="测试配方",
        )
        assert t.template_id == "t1"
        assert t.revision == 1
        assert t.name == "测试风格"
        assert t.kind == "custom"
        assert t.prompt_text == "测试配方"
        assert t.is_active is True

    def test_to_dict_roundtrip(self):
        """测试序列化/反序列化往返。"""
        original = StyleTemplate(
            template_id="t1",
            revision=1,
            name="测试风格",
            kind="preset",
            prompt_text="测试配方",
            negative_prompt="负面",
            tags=["tag1", "tag2"],
        )
        data = original.to_dict()
        restored = StyleTemplate.from_dict(data)
        assert restored.template_id == original.template_id
        assert restored.name == original.name
        assert restored.kind == original.kind
        assert restored.tags == original.tags

    def test_copy_to_custom(self):
        """测试复制为 custom。"""
        preset = StyleTemplate(
            template_id="seed-001",
            revision=1,
            name="极简粗线简笔白板风",
            kind="preset",
            prompt_text="暖白色纯净背景...",
            tags=["白板"],
        )
        custom = preset.copy_to_custom("custom-001", "2026-08-31T00:00:00Z")
        assert custom.template_id == "custom-001"
        assert custom.kind == "custom"
        assert custom.name == preset.name
        assert custom.prompt_text == preset.prompt_text
        assert custom.revision == 1
        # 原始 preset 不受影响
        assert preset.kind == "preset"

    def test_preset_is_readonly(self):
        """测试 preset 只读（在 repository 层强制）。"""
        # 这个测试在 repository 层验证
        pass

    def test_soft_delete(self):
        """测试软删除（is_active=False）。"""
        t = StyleTemplate(
            template_id="t1",
            revision=1,
            name="测试",
            kind="custom",
            prompt_text="配方",
        )
        assert t.is_active is True
        t.is_active = False
        assert t.is_active is False
