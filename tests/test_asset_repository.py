"""测试 FilesystemAssetRepository。"""

import json
import pytest
from pathlib import Path

from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.style_template import StyleTemplate


@pytest.fixture
def repo(tmp_path: Path) -> FilesystemAssetRepository:
    return FilesystemAssetRepository(tmp_path)


class TestStyleTemplates:
    """风格模板 CRUD 测试。"""

    def test_list_empty(self, repo: FilesystemAssetRepository):
        """空仓库返回空列表。"""
        assert repo.list_style_templates() == []

    def test_save_and_get(self, repo: FilesystemAssetRepository):
        """保存和读取。"""
        t = StyleTemplate(
            template_id="t1",
            revision=1,
            name="测试风格",
            kind="custom",
            prompt_text="测试配方",
        )
        repo.save_style_template(t)
        got = repo.get_style_template("t1")
        assert got.name == "测试风格"
        assert got.revision == 1

    def test_save_preset_forbidden(self, repo: FilesystemAssetRepository):
        """preset 禁止修改。"""
        # 先写入一个 preset
        templates_path = repo._templates_path()
        templates_path.write_text(json.dumps([{
            "template_id": "seed-001",
            "revision": 1,
            "name": "极简粗线简笔白板风",
            "kind": "preset",
            "prompt_text": "暖白色纯净背景...",
            "is_active": True,
        }], ensure_ascii=False), encoding="utf-8")

        t = repo.get_style_template("seed-001")
        t.prompt_text = "修改后"
        with pytest.raises(DomainError, match="preset 风格禁止修改"):
            repo.save_style_template(t)

    def test_deactivate_custom(self, repo: FilesystemAssetRepository):
        """停用 custom 模板。"""
        t = StyleTemplate(
            template_id="t1",
            revision=1,
            name="测试",
            kind="custom",
            prompt_text="配方",
        )
        repo.save_style_template(t)
        repo.deactivate_style_template("t1")
        # 停用后不出现在列表中
        assert len(repo.list_style_templates()) == 0

    def test_deactivate_preset_forbidden(self, repo: FilesystemAssetRepository):
        """preset 禁止停用。"""
        templates_path = repo._templates_path()
        templates_path.write_text(json.dumps([{
            "template_id": "seed-001",
            "revision": 1,
            "name": "极简粗线简笔白板风",
            "kind": "preset",
            "prompt_text": "暖白色纯净背景...",
            "is_active": True,
        }], ensure_ascii=False), encoding="utf-8")

        with pytest.raises(DomainError, match="preset 风格禁止停用"):
            repo.deactivate_style_template("seed-001")

    def test_list_by_kind(self, repo: FilesystemAssetRepository):
        """按 kind 筛选。"""
        repo.save_style_template(StyleTemplate(
            template_id="t1", revision=1, name="A", kind="custom", prompt_text="a",
        ))
        repo.save_style_template(StyleTemplate(
            template_id="t2", revision=1, name="B", kind="preset", prompt_text="b",
        ))
        customs = repo.list_style_templates(kind="custom")
        assert len(customs) == 1
        assert customs[0].kind == "custom"

    def test_get_not_found(self, repo: FilesystemAssetRepository):
        """不存在时抛出 NotFoundError。"""
        with pytest.raises(NotFoundError):
            repo.get_style_template("nonexistent")


class TestAssetRef:
    """资产引用测试。"""

    def test_save_and_get(self, repo: FilesystemAssetRepository):
        """保存和读取。"""
        content = b"hello world"
        ref = repo.save_asset(content, "test.txt", "text/plain")
        assert ref.size_bytes == len(content)
        assert ref.mime_type == "text/plain"

        got = repo.get_asset(ref.asset_id)
        assert got.asset_id == ref.asset_id

    def test_hash_dedup(self, repo: FilesystemAssetRepository):
        """相同内容返回相同 asset_id。"""
        content = b"hello world"
        ref1 = repo.save_asset(content, "a.txt", "text/plain")
        ref2 = repo.save_asset(content, "b.txt", "text/plain")
        assert ref1.asset_id == ref2.asset_id

    def test_read_bytes(self, repo: FilesystemAssetRepository):
        """读取文件内容。"""
        content = b"hello world"
        ref = repo.save_asset(content, "test.txt", "text/plain")
        data = repo.read_asset_bytes(ref.asset_id)
        assert data == content

    def test_path_traversal_blocked(self, repo: FilesystemAssetRepository):
        """路径遍历防护。"""
        with pytest.raises(DomainError, match="非法字符"):
            repo.save_asset(b"x", "../etc/passwd", "text/plain")
        with pytest.raises(DomainError, match="非法字符"):
            repo.save_asset(b"x", "/etc/passwd", "text/plain")

    def test_get_not_found(self, repo: FilesystemAssetRepository):
        """不存在时抛出 NotFoundError。"""
        with pytest.raises(NotFoundError):
            repo.get_asset("nonexistent")


class TestVoiceAsset:
    """语音资产测试。"""

    def test_save_and_list(self, repo: FilesystemAssetRepository):
        """保存和列表。"""
        content = b"fake wav content"
        voice = repo.save_voice_asset(content, "测试语音", 5000, 24000, 1, "wav")
        assert voice.name == "测试语音"
        assert voice.duration_ms == 5000

        voices = repo.list_voice_assets()
        assert len(voices) == 1
        assert voices[0].voice_id == voice.voice_id

    def test_deactivate(self, repo: FilesystemAssetRepository):
        """停用语音资产。"""
        content = b"fake wav content"
        voice = repo.save_voice_asset(content, "测试", 5000, 24000, 1, "wav")
        repo.deactivate_voice_asset(voice.voice_id)
        voices = repo.list_voice_assets()
        assert len(voices) == 0

    def test_get_not_found(self, repo: FilesystemAssetRepository):
        """不存在时抛出 NotFoundError。"""
        with pytest.raises(NotFoundError):
            repo.get_voice_asset("nonexistent")
