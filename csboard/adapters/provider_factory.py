"""ProviderFactory — 根据配置构造真实 Adapter。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from csboard.adapters.secrets import SecretStore
from csboard.domain.provider_types import ProviderProfile, ProviderType


class ProviderFactory:
    """根据 ProviderProfile 和 SecretStore 构造 Adapter 实例。"""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._secret_store = SecretStore(data_dir)

    @property
    def secret_store(self) -> SecretStore:
        """获取 SecretStore 实例。"""
        return self._secret_store

    def check_provider(self, profile: ProviderProfile) -> dict[str, Any]:
        """检查 Provider 配置状态。

        Returns:
            {
                "configured": bool,
                "missing_secrets": list[str],
                "configured_secrets": list[str],
            }
        """
        missing = []
        configured = []
        for secret_key in profile.required_secrets:
            full_key = f"{profile.provider_type.value}_{secret_key}"
            if self._secret_store.has(full_key):
                configured.append(secret_key)
            else:
                missing.append(secret_key)
        return {
            "configured": len(missing) == 0,
            "missing_secrets": missing,
            "configured_secrets": configured,
        }

    def check_all_providers(self, profiles: dict[str, ProviderProfile]) -> dict[str, Any]:
        """检查所有 Provider 配置状态。

        Returns:
            {
                "all_configured": bool,
                "providers": dict[str, provider_status],
                "missing": list[str],
                "configured": list[str],
            }
        """
        providers = {}
        missing = []
        configured = []
        for name, profile in profiles.items():
            status = self.check_provider(profile)
            providers[name] = status
            if status["configured"]:
                configured.append(name)
            else:
                missing.append(name)
        return {
            "all_configured": len(missing) == 0,
            "providers": providers,
            "missing": missing,
            "configured": configured,
        }

    def create_text_model(self, profile: ProviderProfile) -> Any:
        """构造 TextModel 适配器。"""
        from csboard.adapters.openai_compatible.text_adapter import OpenAITextAdapter

        secrets = self._get_secrets(profile)
        config = profile.config.copy()
        return OpenAITextAdapter(
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            api_key=secrets.get("api_key", ""),
            model=config.get("model", "gpt-4o"),
            protocol=config.get("api_mode", "chat_completions"),
        )

    def create_image_model(self, profile: ProviderProfile) -> Any:
        """构造 ImageModel 适配器。"""
        from csboard.adapters.openai_compatible.image_adapter import OpenAIImageAdapter

        secrets = self._get_secrets(profile)
        config = profile.config.copy()
        return OpenAIImageAdapter(
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            api_key=secrets.get("api_key", ""),
            model=config.get("model", "gpt-image-1"),
        )

    def create_tts(self, profile: ProviderProfile) -> Any:
        """构造 TTS 适配器。"""
        from csboard.adapters.indextts.tts_adapter import IndexTTSAdapter

        config = profile.config.copy()
        return IndexTTSAdapter(
            base_url=config.get("url", "http://127.0.0.1:7860"),
            mode=config.get("mode", "gradio"),
        )

    def create_alignment(self, profile: ProviderProfile) -> Any:
        """构造 Alignment 适配器。"""
        from csboard.adapters.whisper.alignment_adapter import WhisperAlignmentAdapter
        from pathlib import Path

        config = profile.config.copy()
        # 计算 renderer_root
        renderer_root = Path(__file__).parent.parent.parent / "video_renderer"
        return WhisperAlignmentAdapter(
            mode=config.get("mode", "node"),
            renderer_root=renderer_root if renderer_root.exists() else None,
        )

    def create_renderer(self, profile: ProviderProfile) -> Any:
        """构造 Renderer 适配器。"""
        from csboard.adapters.whiteboard.renderer_adapter import WhiteboardRendererAdapter

        return WhiteboardRendererAdapter()

    def create_media(self, profile: ProviderProfile) -> Any:
        """构造 Media 适配器。"""
        from csboard.adapters.ffmpeg.media_adapter import FFmpegMediaAdapter

        return FFmpegMediaAdapter()

    def _get_secrets(self, profile: ProviderProfile) -> dict[str, str]:
        """获取 Provider 的所有 secret。"""
        secrets = {}
        for secret_key in profile.required_secrets + profile.optional_secrets:
            full_key = f"{profile.provider_type.value}_{secret_key}"
            value = self._secret_store.get(full_key)
            if value:
                secrets[secret_key] = value
        return secrets
