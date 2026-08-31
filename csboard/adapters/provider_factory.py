"""ProviderFactory — 根据配置构造真实 Adapter。

ProviderFactory 是 MountainCommands/Pipeline 的唯一 Provider 构造入口。
禁止从 request.json 读取 API Key。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from csboard.adapters.secrets import SecretStoreProtocol, create_secret_store, mask_secret
from csboard.domain.errors import DomainError
from csboard.domain.provider_types import ProviderProfile, ProviderType


class ProviderFactory:
    """根据 ServiceDefinition 和 SecretStore 构造 Adapter 实例。

    新的生产路径通过 create_adapter(service_definition) 构造 Adapter。
    SecretStore 必须由外部注入（单一组合根），不得自行创建。
    """

    def __init__(
        self,
        data_dir: Path,
        secret_store: SecretStoreProtocol | None = None,
        is_encrypted: bool = True,
        **kwargs: Any,
    ) -> None:
        self._data_dir = data_dir
        self._profiles_dir = data_dir / ".profiles"
        self._profiles_dir.mkdir(parents=True, exist_ok=True)
        if secret_store is not None:
            self._secret_store = secret_store
            self._is_encrypted = is_encrypted
        else:
            # 兼容旧调用：自行创建（但生产路径应注入）
            encrypted = kwargs.get("encrypted", True)
            self._secret_store, self._is_encrypted = create_secret_store(data_dir, encrypted)
        self._profiles: dict[str, ProviderProfile] = {}
        self._load_profiles()

    @property
    def secret_store(self) -> SecretStoreProtocol:
        """获取 SecretStore 实例。"""
        return self._secret_store

    @property
    def is_encrypted(self) -> bool:
        """SecretStore 是否使用加密。"""
        return self._is_encrypted

    def _load_profiles(self) -> None:
        """加载持久化的 Provider Profile。"""
        from csboard.domain.provider_types import PROVIDER_PROFILES
        # 使用默认 profile 作为基础
        self._profiles = dict(PROVIDER_PROFILES)
        # 加载用户自定义配置
        for profile_file in self._profiles_dir.glob("*.json"):
            try:
                data = json.loads(profile_file.read_text(encoding="utf-8"))
                name = profile_file.stem
                if name in self._profiles:
                    # 合并用户配置到默认 profile
                    profile = self._profiles[name]
                    config = {**profile.config, **data.get("config", {})}
                    self._profiles[name] = ProviderProfile(
                        provider_type=profile.provider_type,
                        name=profile.name,
                        description=profile.description,
                        required_secrets=profile.required_secrets,
                        optional_secrets=profile.optional_secrets,
                        config=config,
                    )
            except (json.JSONDecodeError, OSError):
                continue

    def _save_profile(self, name: str, profile: ProviderProfile) -> None:
        """持久化 Provider Profile（仅非敏感配置）。"""
        profile_path = self._profiles_dir / f"{name}.json"
        data = {"config": profile.config}
        profile_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get_profile(self, name: str) -> ProviderProfile | None:
        """获取 Provider Profile。"""
        return self._profiles.get(name)

    def update_profile_config(self, name: str, config: dict[str, Any]) -> None:
        """更新 Provider Profile 的非敏感配置。

        仅允许更新 profile 默认 config 中已声明的 key。
        """
        if name not in self._profiles:
            raise ValueError(f"Provider '{name}' 不存在")
        profile = self._profiles[name]
        allowed_keys = set(profile.config.keys())
        # 从默认 PROVIDER_PROFILES 获取允许的 key（而非合并后的）
        from csboard.domain.provider_types import PROVIDER_PROFILES
        default_profile = PROVIDER_PROFILES.get(name)
        if default_profile:
            allowed_keys = set(default_profile.config.keys())
        unknown_keys = set(config.keys()) - allowed_keys
        if unknown_keys:
            raise ValueError(
                f"不允许更新未知字段: {', '.join(sorted(unknown_keys))}。"
                f"允许的字段: {', '.join(sorted(allowed_keys)) if allowed_keys else '(无)'}"
            )
        new_config = {**profile.config, **config}
        self._profiles[name] = ProviderProfile(
            provider_type=profile.provider_type,
            name=profile.name,
            description=profile.description,
            required_secrets=profile.required_secrets,
            optional_secrets=profile.optional_secrets,
            config=new_config,
        )
        self._save_profile(name, self._profiles[name])

    def check_provider(self, name: str) -> dict[str, Any]:
        """检查 Provider 配置状态。

        Returns:
            {
                "configured": bool,
                "missing_secrets": list[str],
                "configured_secrets": list[str],
                "is_encrypted": bool,
            }
        """
        profile = self._profiles.get(name)
        if profile is None:
            return {
                "configured": False,
                "missing_secrets": [],
                "configured_secrets": [],
                "is_encrypted": self._is_encrypted,
            }
        missing = []
        configured = []
        for secret_key in profile.required_secrets:
            full_key = f"{profile.provider_type.value}_{secret_key}"
            if self._secret_store.get(full_key) is not None:
                configured.append(secret_key)
            else:
                missing.append(secret_key)
        return {
            "configured": len(missing) == 0,
            "missing_secrets": missing,
            "configured_secrets": configured,
            "is_encrypted": self._is_encrypted,
        }

    def check_all_providers(self) -> dict[str, Any]:
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
        for name in self._profiles:
            status = self.check_provider(name)
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

    def check_all_availability(self) -> dict[str, Any]:
        """检查所有 Provider 实际可用性（配置 + 连接测试）。

        Returns:
            {
                "all_available": bool,
                "providers": dict[str, availability_status],
                "unavailable": list[str],
            }
        """
        providers = {}
        unavailable = []
        for name in self._profiles:
            status = self.check_provider_availability(name)
            providers[name] = status
            if not status["available"]:
                unavailable.append(name)
        return {
            "all_available": len(unavailable) == 0,
            "providers": providers,
            "unavailable": unavailable,
        }

    def check_provider_availability(self, name: str) -> dict[str, Any]:
        """检查 Provider 实际可用性（连接测试）。

        Returns:
            {
                "available": bool,
                "component": str,
                "error_code": str | None,
                "suggestion": str | None,
            }
        """
        profile = self._profiles.get(name)
        if profile is None:
            return {
                "available": False,
                "component": name,
                "error_code": "PROVIDER_NOT_FOUND",
                "suggestion": f"Provider '{name}' 不存在",
            }

        # 检查 secret 是否配置
        secret_status = self.check_provider(name)
        if not secret_status["configured"]:
            return {
                "available": False,
                "component": name,
                "error_code": "SECRET_NOT_CONFIGURED",
                "suggestion": f"请配置 {', '.join(secret_status['missing_secrets'])}",
            }

        # 根据 provider 类型检查可用性
        if profile.provider_type == ProviderType.TEXT_TO_SPEECH:
            return self._check_tts_availability(profile)
        elif profile.provider_type == ProviderType.ALIGNMENT:
            return self._check_alignment_availability(profile)
        elif profile.provider_type == ProviderType.RENDERER:
            return self._check_renderer_availability(profile)
        elif profile.provider_type == ProviderType.MEDIA:
            return self._check_media_availability(profile)
        elif profile.provider_type in (ProviderType.TEXT_MODEL, ProviderType.IMAGE_MODEL):
            # API 类型只检查 secret 是否存在
            return {
                "available": True,
                "component": name,
                "error_code": None,
                "suggestion": None,
            }

        return {
            "available": True,
            "component": name,
            "error_code": None,
            "suggestion": None,
        }

    def _check_tts_availability(self, profile: ProviderProfile) -> dict[str, Any]:
        """检查 TTS 服务可用性。"""
        import httpx
        url = profile.config.get("url", "http://127.0.0.1:7860")
        mode = profile.config.get("mode", "gradio")
        try:
            if mode == "fastapi":
                with httpx.Client(timeout=5) as client:
                    response = client.get(f"{url}/health")
                    if response.status_code == 200:
                        return {"available": True, "component": "tts", "error_code": None, "suggestion": None}
            else:
                # Gradio 模式，尝试连接
                with httpx.Client(timeout=5) as client:
                    response = client.get(f"{url}/")
                    if response.status_code == 200:
                        return {"available": True, "component": "tts", "error_code": None, "suggestion": None}
            return {
                "available": False,
                "component": "tts",
                "error_code": "TTS_UNREACHABLE",
                "suggestion": f"IndexTTS 服务 {url} 不可达，请确认服务已启动",
            }
        except (httpx.ConnectError, httpx.TimeoutException):
            return {
                "available": False,
                "component": "tts",
                "error_code": "TTS_UNREACHABLE",
                "suggestion": f"IndexTTS 服务 {url} 不可达，请确认服务已启动",
            }

    def _check_alignment_availability(self, profile: ProviderProfile) -> dict[str, Any]:
        """检查 Alignment 服务可用性。"""
        import shutil
        mode = profile.config.get("mode", "node")
        if mode == "node":
            # 检查 node 和 align.mjs 是否存在
            node = shutil.which("node")
            if not node:
                return {
                    "available": False,
                    "component": "alignment",
                    "error_code": "NODE_NOT_FOUND",
                    "suggestion": "请安装 Node.js",
                }
            renderer_root = self._data_dir.parent / "video_renderer"
            align_script = renderer_root / "align.mjs"
            if not align_script.exists():
                return {
                    "available": False,
                    "component": "alignment",
                    "error_code": "ALIGN_SCRIPT_NOT_FOUND",
                    "suggestion": f"对齐脚本 {align_script} 不存在",
                }
            return {"available": True, "component": "alignment", "error_code": None, "suggestion": None}
        else:
            # HTTP 模式
            import httpx
            url = profile.config.get("base_url", "http://127.0.0.1:9000")
            try:
                with httpx.Client(timeout=5) as client:
                    response = client.get(f"{url}/health")
                    if response.status_code == 200:
                        return {"available": True, "component": "alignment", "error_code": None, "suggestion": None}
                return {
                    "available": False,
                    "component": "alignment",
                    "error_code": "WHISPER_UNREACHABLE",
                    "suggestion": f"Whisper 服务 {url} 不可达",
                }
            except (httpx.ConnectError, httpx.TimeoutException):
                return {
                    "available": False,
                    "component": "alignment",
                    "error_code": "WHISPER_UNREACHABLE",
                    "suggestion": f"Whisper 服务 {url} 不可达",
                }

    def _check_renderer_availability(self, profile: ProviderProfile) -> dict[str, Any]:
        """检查 Renderer 可用性。"""
        import shutil
        python = shutil.which("python3") or shutil.which("python")
        if not python:
            return {
                "available": False,
                "component": "renderer",
                "error_code": "PYTHON_NOT_FOUND",
                "suggestion": "请安装 Python",
            }
        render_script = self._data_dir.parent / "scripts" / "render_stream_whiteboard.py"
        if not render_script.exists():
            return {
                "available": False,
                "component": "renderer",
                "error_code": "RENDER_SCRIPT_NOT_FOUND",
                "suggestion": f"渲染脚本 {render_script} 不存在",
            }
        return {"available": True, "component": "renderer", "error_code": None, "suggestion": None}

    def _check_media_availability(self, profile: ProviderProfile) -> dict[str, Any]:
        """检查 Media (FFmpeg) 可用性。"""
        import shutil
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if not ffmpeg:
            return {
                "available": False,
                "component": "media",
                "error_code": "FFMPEG_NOT_FOUND",
                "suggestion": "请安装 FFmpeg",
            }
        if not ffprobe:
            return {
                "available": False,
                "component": "media",
                "error_code": "FFPROBE_NOT_FOUND",
                "suggestion": "请安装 FFmpeg (包含 ffprobe)",
            }
        return {"available": True, "component": "media", "error_code": None, "suggestion": None}

    def create_text_model(self) -> Any:
        """构造 TextModel 适配器。"""
        from csboard.adapters.openai_compatible.text_adapter import OpenAITextAdapter

        profile = self._profiles.get("text_model")
        if profile is None:
            raise ValueError("text_model profile 不存在")

        secrets = self._get_secrets(profile)
        config = profile.config.copy()
        return OpenAITextAdapter(
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            api_key=secrets.get("api_key", ""),
            model=config.get("model", "gpt-4o"),
            protocol=config.get("api_mode", "chat_completions"),
        )

    def create_image_model(self) -> Any:
        """构造 ImageModel 适配器。"""
        from csboard.adapters.openai_compatible.image_adapter import OpenAIImageAdapter

        profile = self._profiles.get("image_model")
        if profile is None:
            raise ValueError("image_model profile 不存在")

        secrets = self._get_secrets(profile)
        config = profile.config.copy()
        return OpenAIImageAdapter(
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            api_key=secrets.get("api_key", ""),
            model=config.get("model", "gpt-image-1"),
        )

    def create_tts(self) -> Any:
        """构造 TTS 适配器。"""
        from csboard.adapters.indextts.tts_adapter import IndexTTSAdapter

        profile = self._profiles.get("tts")
        if profile is None:
            raise ValueError("tts profile 不存在")

        config = profile.config.copy()
        return IndexTTSAdapter(
            base_url=config.get("url", "http://127.0.0.1:7860"),
            mode=config.get("mode", "gradio"),
        )

    def create_alignment(self) -> Any:
        """构造 Alignment 适配器。"""
        from csboard.adapters.whisper.alignment_adapter import WhisperAlignmentAdapter

        profile = self._profiles.get("alignment")
        if profile is None:
            raise ValueError("alignment profile 不存在")

        config = profile.config.copy()
        renderer_root = self._data_dir.parent / "video_renderer"
        return WhisperAlignmentAdapter(
            mode=config.get("mode", "node"),
            renderer_root=renderer_root if renderer_root.exists() else None,
            base_url=config.get("base_url", "http://127.0.0.1:9000"),
        )

    def create_renderer(self) -> Any:
        """构造 Renderer 适配器。"""
        from csboard.adapters.whiteboard.renderer_adapter import WhiteboardRendererAdapter

        return WhiteboardRendererAdapter()

    def create_media(self) -> Any:
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

    def get_secret_value(self, secret_key: str) -> str | None:
        """获取单个 secret 值（内部使用）。"""
        return self._secret_store.get(secret_key)

    def create_adapter(self, service_definition: Any) -> Any:
        """根据 ServiceDefinition 构造 Adapter。

        adapter_type 支持：
        - openai_compatible → OpenAITextAdapter / OpenAIImageAdapter（按 capability）
        - indextts → IndexTTSAdapter
        - whisper → WhisperAlignmentAdapter
        - ffmpeg → FFmpegMediaAdapter
        - local_process → WhiteboardRendererAdapter
        - codex_skill → CodexSkillAdapter（预留）

        未知 adapter_type 抛出 UNSUPPORTED_ADAPTER。
        """
        adapter_type = service_definition.adapter_type
        capability = service_definition.capability
        config = service_definition.config.copy()
        endpoint = service_definition.endpoint or ""

        # 收集 secrets
        secrets: dict[str, str] = {}
        for key in service_definition.required_secrets + service_definition.optional_secrets:
            full_key = f"{service_definition.service_id}_{key}"
            value = self._secret_store.get(full_key)
            if value:
                secrets[key] = value

        if adapter_type == "openai_compatible":
            if capability == "text_generation":
                from csboard.adapters.openai_compatible.text_adapter import OpenAITextAdapter
                return OpenAITextAdapter(
                    base_url=endpoint or config.get("base_url", "https://api.openai.com/v1"),
                    api_key=secrets.get("api_key", ""),
                    model=service_definition.model or config.get("model", "gpt-4o"),
                    protocol=config.get("api_mode", "chat_completions"),
                )
            elif capability == "image_generation":
                from csboard.adapters.openai_compatible.image_adapter import OpenAIImageAdapter
                return OpenAIImageAdapter(
                    base_url=endpoint or config.get("base_url", "https://api.openai.com/v1"),
                    api_key=secrets.get("api_key", ""),
                    model=service_definition.model or config.get("model", "gpt-image-1"),
                )
            else:
                raise DomainError("UNSUPPORTED_ADAPTER", f"openai_compatible 不支持 capability: {capability}")

        elif adapter_type == "indextts":
            from csboard.adapters.indextts.tts_adapter import IndexTTSAdapter
            return IndexTTSAdapter(
                base_url=endpoint or "http://127.0.0.1:7860",
                mode=config.get("mode", "gradio"),
            )

        elif adapter_type == "whisper":
            from csboard.adapters.whisper.alignment_adapter import WhisperAlignmentAdapter
            renderer_root = self._data_dir.parent / "video_renderer"
            return WhisperAlignmentAdapter(
                mode=config.get("mode", "node"),
                renderer_root=renderer_root if renderer_root.exists() else None,
                base_url=endpoint or "http://127.0.0.1:9000",
            )

        elif adapter_type == "ffmpeg":
            from csboard.adapters.ffmpeg.media_adapter import FFmpegMediaAdapter
            return FFmpegMediaAdapter()

        elif adapter_type == "local_process":
            from csboard.adapters.whiteboard.renderer_adapter import WhiteboardRendererAdapter
            return WhiteboardRendererAdapter()

        elif adapter_type == "codex_skill":
            raise DomainError("UNSUPPORTED_ADAPTER", "codex_skill 适配器尚未实现")

        else:
            raise DomainError("UNSUPPORTED_ADAPTER", f"未知 adapter_type: {adapter_type}")
