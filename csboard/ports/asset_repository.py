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

    def list_style_templates(self, kind: str | None = None, status: str | None = None) -> list[StyleTemplate]:
        """列出风格模板。kind=None/status=None 表示全部。"""
        ...

    def get_style_template(self, style_id: str) -> StyleTemplate:
        """获取单个风格模板。不存在时抛出 NotFoundError。"""
        ...

    def save_style_template(self, template: StyleTemplate) -> None:
        """保存风格模板（创建或更新）。preset 禁止修改。"""
        ...

    def deactivate_style_template(self, style_id: str) -> None:
        """标记自定义风格为 inactive。"""
        ...

    def activate_style_template(self, style_id: str) -> None:
        """标记风格为 active。"""
        ...

    # ── VoiceAsset ─────────────────────────────────────────────────

    def list_voice_assets(self) -> list[VoiceAsset]:
        """列出语音资产。"""
        ...

    def get_voice_asset(self, voice_id: str) -> VoiceAsset:
        """获取单个语音资产。不存在时抛出 NotFoundError。"""
        ...

    def save_voice_asset(self, content: bytes, name: str, duration_ms: int, sample_rate: int, channels: int, format_ext: str) -> VoiceAsset:
        """保存语音资产（内容 + 元数据）。"""
        ...

    def deactivate_voice_asset(self, voice_id: str) -> None:
        """标记语音为 inactive。"""
        ...

    def activate_voice_asset(self, voice_id: str) -> None:
        """标记语音为 active。"""
        ...

    def get_voice_content(self, voice_id: str) -> bytes:
        """读取语音二进制内容。"""
        ...

    # ── AssetRef ───────────────────────────────────────────────────

    def save_asset(self, content: bytes, filename: str, media_type: str | None = None, project_id: str | None = None) -> AssetRef:
        ...

    def get_asset(self, asset_id: str) -> AssetRef | None:
        ...

    def get_asset_content(self, asset_id: str) -> bytes:
        ...
