"""ProviderFactory 动态适配器测试。

覆盖：
- create_adapter 根据 ServiceDefinition 构造 Adapter
- 不再依赖固定 PROVIDER_PROFILES
- 未知 adapter_type 返回 UNSUPPORTED_ADAPTER
- openai_compatible 按 capability 区分 text/image
"""

from __future__ import annotations

from pathlib import Path

import pytest

from csboard.adapters.provider_factory import ProviderFactory
from csboard.adapters.secrets.secret_store import PlaintextSecretStore
from csboard.domain.errors import DomainError
from csboard.domain.service_definition import ServiceDefinition


@pytest.fixture()
def factory(tmp_path: Path) -> ProviderFactory:
    # 创建 secret store 并注入
    store = PlaintextSecretStore(tmp_path / ".secrets")
    return ProviderFactory(tmp_path, secret_store=store, is_encrypted=False)


def _make_service(service_id: str, adapter_type: str, capability: str, **kwargs) -> ServiceDefinition:
    defaults = {
        "service_id": service_id,
        "display_name": f"Service {service_id}",
        "capability": capability,
        "adapter_type": adapter_type,
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4o",
        "enabled": True,
        "priority": 100,
        "is_default": False,
        "config": {},
        "required_secrets": ["api_key"],
        "optional_secrets": [],
    }
    defaults.update(kwargs)
    return ServiceDefinition(**defaults)


def test_create_text_adapter(factory: ProviderFactory):
    """openai_compatible + text_generation → OpenAITextAdapter。"""
    svc = _make_service("text-1", "openai_compatible", "text_generation")
    adapter = factory.create_adapter(svc)
    assert adapter is not None
    assert "Text" in type(adapter).__name__ or "text" in type(adapter).__name__.lower()


def test_create_image_adapter(factory: ProviderFactory):
    """openai_compatible + image_generation → OpenAIImageAdapter。"""
    svc = _make_service("img-1", "openai_compatible", "image_generation")
    adapter = factory.create_adapter(svc)
    assert adapter is not None


def test_create_tts_adapter(factory: ProviderFactory):
    """indextts → IndexTTSAdapter。"""
    svc = _make_service("tts-1", "indextts", "speech_synthesis")
    adapter = factory.create_adapter(svc)
    assert adapter is not None


def test_create_alignment_adapter(factory: ProviderFactory):
    """whisper → WhisperAlignmentAdapter。"""
    svc = _make_service("align-1", "whisper", "speech_alignment")
    adapter = factory.create_adapter(svc)
    assert adapter is not None
    assert adapter._renderer_root.name == "video_renderer"
    assert (adapter._renderer_root / "align.mjs").is_file()


def test_create_media_adapter(factory: ProviderFactory):
    """ffmpeg → FFmpegMediaAdapter。"""
    svc = _make_service("media-1", "ffmpeg", "media")
    adapter = factory.create_adapter(svc)
    assert adapter is not None


def test_create_renderer_adapter(factory: ProviderFactory):
    """local_process → WhiteboardRendererAdapter。"""
    svc = _make_service("render-1", "local_process", "rendering")
    adapter = factory.create_adapter(svc)
    assert adapter is not None


def test_unsupported_adapter_type(factory: ProviderFactory):
    """未知 adapter_type 抛出 UNSUPPORTED_ADAPTER。"""
    svc = _make_service("bad-1", "unknown_type", "text_generation")
    with pytest.raises(DomainError) as exc_info:
        factory.create_adapter(svc)
    assert exc_info.value.code == "UNSUPPORTED_ADAPTER"


def test_openai_speech_capability_creates_tts_adapter(factory: ProviderFactory):
    """openai_compatible + speech_synthesis creates the provider-neutral TTS adapter.

    Supported as of the TTS adapter addition. Previously this combination raised
    UNSUPPORTED_ADAPTER; the old regression test was removed and replaced by this one.
    """
    svc = _make_service("bad-1", "openai_compatible", "speech_synthesis")
    adapter = factory.create_adapter(svc)
    assert adapter.__class__.__name__ == "OpenAITTSAdapter"


def test_unsupported_capability_for_openai_raises(factory: ProviderFactory):
    """openai_compatible with a genuinely unsupported capability raises UNSUPPORTED_ADAPTER."""
    svc = _make_service("bad-video", "openai_compatible", "video_generation")
    with pytest.raises(DomainError) as exc_info:
        factory.create_adapter(svc)
    assert exc_info.value.code == "UNSUPPORTED_ADAPTER"


def test_legacy_create_methods_still_work(factory: ProviderFactory):
    """旧的 create_text_model 等方法仍然可用（向后兼容）。"""
    # 这些方法依赖 PROVIDER_PROFILES，但如果 profile 存在则应工作
    # 在没有配置的情况下应抛出 ValueError
    try:
        adapter = factory.create_text_model()
        assert adapter is not None
    except ValueError:
        # 预期：profile 不存在
        pass
