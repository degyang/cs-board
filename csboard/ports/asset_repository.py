"""AssetRepository — 资产仓储端口。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from csboard.domain.asset_ref import AssetRef
from csboard.domain.style_template import StyleTemplate
from csboard.domain.voice_asset import VoiceAsset


@runtime_checkable
class AssetRepository(Protocol):
    """资产仓储接口。"""

    # ── StyleTemplate ──────────────────────────────────────────────

    def list_style_templates(self, kind: str | None = None) -> list[StyleTemplate]:
        """列出风格模板。kind=None 表示全部。"""
        ...

    def get_style_template(self, template_id: str) -> StyleTemplate:
        """获取单个风格模板。不存在时抛出 NotFoundError。"""
        ...

    def save_style_template(self, template: StyleTemplate) -> None:
        """保存风格模板（创建或更新）。"""
        ...

    def deactivate_style_template(self, template_id: str) -> None:
        """停用风格模板（软删除）。preset 禁止停用。"""
        ...

    # ── AssetRef ───────────────────────────────────────────────────

    def save_asset(self, file_bytes: bytes, original_name: str, mime_type: str) -> AssetRef:
        """保存资产文件。hash 去重：相同内容返回已有 AssetRef。"""
        ...

    def get_asset(self, asset_id: str) -> AssetRef:
        """获取资产引用。不存在时抛出 NotFoundError。"""
        ...

    def read_asset_bytes(self, asset_id: str) -> bytes:
        """读取资产文件内容。路径逃逸时抛出 DomainError。"""
        ...

    # ── VoiceAsset ─────────────────────────────────────────────────

    def save_voice_asset(self, file_bytes: bytes, name: str, duration_ms: int, sample_rate: int, channels: int, audio_format: str) -> VoiceAsset:
        """保存语音资产。"""
        ...

    def get_voice_asset(self, voice_id: str) -> VoiceAsset:
        """获取语音资产。不存在时抛出 NotFoundError。"""
        ...

    def list_voice_assets(self) -> list[VoiceAsset]:
        """列出所有活跃语音资产。"""
        ...

    def deactivate_voice_asset(self, voice_id: str) -> None:
        """停用语音资产（软删除）。"""
        ...
