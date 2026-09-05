"""Read-only Provider-neutral voice profile catalog."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import replace
from pathlib import Path
from typing import Any

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.domain.provider_types import TTSRequest
from csboard.domain.voice_profile import VoiceProfile, VoiceStyleProfile


DEFAULT_VOICE_PREVIEW_TEXT = "这是一个语音测试，我会用清晰的语音提醒你，我就是你知心的助手。"


class VoiceProfileCatalog:
    """Project non-sensitive profile metadata from configured services.

    Providers publish metadata in service ``config``. Credentials are resolved
    only by the registry and are never copied into these DTOs.
    """

    def __init__(self, registry: FilesystemServiceRegistry, data_dir: Path) -> None:
        self._registry = registry
        self._data_dir = data_dir
        self._profiles_dir = self._data_dir / "settings" / "voice-profiles"
        self._styles_dir = self._data_dir / "settings" / "voice-style-profiles"
        self._profiles_dir.mkdir(parents=True, exist_ok=True)
        self._styles_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_id(value: str) -> str:
        if not value or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for ch in value):
            raise ValueError("profile id must be a simple identifier")
        return value

    def _provider(self, provider_id: str):
        service = self._registry.get_service(provider_id)
        if not service.enabled or service.capability not in {"speech_synthesis", "audio_generation"}:
            raise ValueError("provider must be enabled and support speech.synthesize")
        if not self._registry.has_required_secrets(service):
            raise ValueError("provider credentials are not configured")
        return service

    @staticmethod
    def _write(path: Path, value: dict[str, Any]) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)

    def create_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider_id = str(payload.get("provider_id", ""))
        service = self._provider(provider_id)
        kind = str(payload.get("kind", ""))
        if kind not in {"provider-preset", "provider-designed"}:
            raise ValueError("unsupported voice profile kind")
        if kind == "provider-preset" and not str(payload.get("remote_voice_id", "")):
            raise ValueError("provider-preset requires remote_voice_id")
        if kind == "provider-designed" and not str(payload.get("design_prompt", "")):
            raise ValueError("provider-designed requires design_prompt")
        model_id = str(payload.get("model_id") or str(service.model).split(",", 1)[0].strip())
        if kind == "provider-preset":
            requested_identity = tuple(self._identity_part(value) for value in (provider_id, model_id, payload.get("remote_voice_id")))
            # Repeat posts are idempotent, including when the current entry is
            # provider metadata or an adapter default rather than a local file.
            existing = next((item for item in self.snapshot()["profiles"] if self._preset_identity(item) == requested_identity), None)
            if existing is not None:
                return {key: value for key, value in existing.items() if key != "identity_key"}
            supplied_id = str(payload.get("profile_id") or "")
            profile_id = self._safe_id(supplied_id) if supplied_id else self._preset_profile_id(requested_identity)
        else:
            profile_id = self._safe_id(str(payload.get("profile_id", "")))
        path = self._profiles_dir / f"{profile_id}.json"
        if path.exists():
            raise ValueError("profile already exists")
        profile = VoiceProfile(profile_id=profile_id, revision=1, name=str(payload.get("name", "")), kind=kind,
                               provider_id=provider_id, model_id=model_id,
                               vendor_id=payload.get("vendor_id"), vendor_name=payload.get("vendor_name"),
                               remote_voice_id=payload.get("remote_voice_id"), design_prompt=payload.get("design_prompt"),
                               default_style_profile_id=payload.get("default_style_profile_id"), language=payload.get("language"),
                               gender=payload.get("gender"),
                               tags=tuple(str(tag) for tag in payload.get("tags", [])), status="active",
                               capability_snapshot={"speech.synthesize": True, "adapter_type": service.adapter_type})
        self._write(path, profile.to_dict())
        return profile.to_dict()

    def create_style(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider_id = payload.get("provider_id")
        if provider_id is not None:
            self._provider(str(provider_id))
        style_id = self._safe_id(str(payload.get("style_profile_id", "")))
        if not str(payload.get("instruction", "")):
            raise ValueError("instruction is required")
        path = self._styles_dir / f"{style_id}.json"
        if path.exists():
            raise ValueError("style profile already exists")
        style = VoiceStyleProfile(style_profile_id=style_id, revision=1, name=str(payload.get("name", "")),
                                  provider_id=str(provider_id) if provider_id is not None else None,
                                  instruction=str(payload["instruction"]), tags=tuple(str(tag) for tag in payload.get("tags", [])),
                                  status="active")
        self._write(path, style.to_dict())
        return style.to_dict()

    def _stored(self, directory: Path) -> list[dict[str, Any]]:
        result = []
        for path in sorted(directory.glob("*.json")):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(value, dict):
                    result.append(value)
            except (OSError, json.JSONDecodeError):
                continue
        return result

    @staticmethod
    def _identity_part(value: object) -> str:
        return unicodedata.normalize("NFKC", str(value or "")).strip().casefold()

    @classmethod
    def _preset_identity(cls, profile: dict[str, Any]) -> tuple[str, str, str] | None:
        """Stable remote-preset identity: service, model, and remote voice only."""
        if profile.get("kind") != "provider-preset":
            return None
        identity = tuple(cls._identity_part(profile.get(key)) for key in ("provider_id", "model_id", "remote_voice_id"))
        return identity if all(identity) else None

    @staticmethod
    def _preset_profile_id(identity: tuple[str, str, str]) -> str:
        """Derive a legal local ID from the normalized provider-owned identity."""
        if not all(identity):
            raise ValueError("provider-preset requires provider_id, model_id and remote_voice_id")
        return "preset-" + hashlib.sha256("\x1f".join(identity).encode("utf-8")).hexdigest()

    @classmethod
    def _deduplicate_profiles(cls, candidates: list[tuple[int, dict[str, Any]]]) -> list[dict[str, Any]]:
        """Use stored override > configured metadata > adapter defaults deterministically."""
        selected: dict[tuple[str, str, str], tuple[int, tuple[str, str], dict[str, Any]]] = {}
        others: list[dict[str, Any]] = []
        for source, profile in candidates:
            identity = cls._preset_identity(profile)
            if identity is None:
                others.append(profile)
                continue
            rank = (cls._identity_part(profile.get("profile_id")), json.dumps(profile, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            current = selected.get(identity)
            if current is None or (source, rank) < (current[0], current[1]):
                selected[identity] = (source, rank, profile)
        profiles = others + [item[2] for _, item in sorted(selected.items())]
        for profile in profiles:
            identity = cls._preset_identity(profile)
            if identity:
                profile["identity_key"] = "|".join(identity)
        return sorted(profiles, key=lambda item: (cls._identity_part(item.get("provider_id")), cls._identity_part(item.get("profile_id"))))

    def profiles(self, provider_id: str | None = None) -> list[dict[str, Any]]:
        values = self._stored(self._profiles_dir)
        return [v for v in values if provider_id is None or v.get("provider_id") == provider_id]

    def update_profile(self, profile_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist an editable override, including for an adapter-generated preset."""
        profile_id = self._safe_id(profile_id)
        current = next((item for item in self.snapshot()["profiles"] if item.get("profile_id") == profile_id), None)
        if current is None:
            raise ValueError("VOICE_PROFILE_NOT_FOUND")
        allowed = {"name", "model_id", "remote_voice_id", "design_prompt", "default_style_profile_id", "language", "gender", "tags", "status"}
        value = {key: current.get(key) for key in VoiceProfile.__dataclass_fields__}
        value.update({key: payload[key] for key in allowed if key in payload})
        value.update(profile_id=profile_id, provider_id=current["provider_id"], revision=int(current.get("revision", 0)) + 1)
        value["tags"] = tuple(str(tag) for tag in value.get("tags") or [])
        service = self._registry.get_service(str(value["provider_id"]))
        models = {self._identity_part(model) for model in str(service.model).split(",") if model.strip()}
        if self._identity_part(value.get("model_id")) not in models:
            raise ValueError("VOICE_PROFILE_MODEL_UNAVAILABLE")
        profile = VoiceProfile(**value)
        self._write(self._profiles_dir / f"{profile_id}.json", profile.to_dict())
        return profile.to_dict()

    def styles(self, provider_id: str | None = None) -> list[dict[str, Any]]:
        values = self._stored(self._styles_dir)
        return [v for v in values if provider_id is None or v.get("provider_id") == provider_id]

    def preview_path(self, profile_id: str) -> Path:
        return self._data_dir / "settings" / "voice-previews" / f"{self._safe_id(profile_id)}.wav"

    def preview(self, profile_id: str, provider_factory: Any, text: str | None = None) -> dict[str, Any]:
        profile = next((p for p in self.snapshot()["profiles"] if p.get("profile_id") == profile_id), None)
        if profile is None:
            raise ValueError("VOICE_PROFILE_NOT_FOUND")
        preview_text = (text or DEFAULT_VOICE_PREVIEW_TEXT).strip()
        if not preview_text or len(preview_text) > 500:
            raise ValueError("VOICE_PREVIEW_TEXT_INVALID")
        service = self._provider(str(profile["provider_id"]))
        path = self.preview_path(profile_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Do not leave old audio addressable when the new provider request fails.
        path.unlink(missing_ok=True)
        declared_models = {self._identity_part(model): model.strip() for model in str(service.model).split(",") if model.strip()}
        model_id = self._identity_part(profile.get("model_id"))
        if model_id not in declared_models:
            raise ValueError("VOICE_PROFILE_MODEL_UNAVAILABLE")
        result = provider_factory.create_adapter(replace(service, model=declared_models[model_id])).synthesize(TTSRequest(
            text=preview_text,
            voice_id=str(profile.get("remote_voice_id") or ""), voice_config={"format": "wav"}, request_id="voice-preview"))
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(result.audio)
        tmp.replace(path)
        return {"profile_id": profile_id, "audio_url": f"/api/v1/voice-profiles/{profile_id}/preview", "content_type": "audio/wav", "duration_ms": result.duration_ms}

    def snapshot(self) -> dict[str, list[dict[str, Any]]]:
        profile_candidates: list[tuple[int, dict[str, Any]]] = []
        styles: list[dict[str, Any]] = []
        capabilities: list[dict[str, Any]] = []
        services = self._registry.list_services(capability="speech_synthesis") + self._registry.list_services(capability="audio_generation")
        for service in services:
            metadata = service.config.get("voice_profiles", [])
            if not isinstance(metadata, list):
                metadata = []
            metadata_with_source: list[tuple[int, dict[str, Any]]] = [(1, item) for item in metadata if isinstance(item, dict)]
            if service.adapter_type == "openai_compatible":
                from csboard.adapters.openai_compatible.tts_adapter import preset_voice_profiles
                metadata_with_source.extend((2, item) for item in preset_voice_profiles(service))
            for source, item in metadata_with_source:
                try:
                    profile = VoiceProfile(
                        profile_id=str(item["profile_id"]), revision=int(item.get("revision", 1)),
                        name=str(item["name"]), kind=str(item["kind"]),
                        provider_id=service.service_id, model_id=str(item.get("model_id") or service.model),
                        vendor_id=item.get("vendor_id"), vendor_name=item.get("vendor_name"),
                        remote_voice_id=item.get("remote_voice_id"), design_prompt=item.get("design_prompt"),
                        default_style_profile_id=item.get("default_style_profile_id"),
                        language=item.get("language"), gender=item.get("gender"), tags=tuple(str(tag) for tag in item.get("tags", [])),
                        status=str(item.get("status", "active")),
                        capability_snapshot={"speech.synthesize": True, "adapter_type": service.adapter_type},
                    )
                except (KeyError, TypeError, ValueError):
                    continue
                profile_candidates.append((source, profile.to_dict()))
            style_metadata = service.config.get("voice_style_profiles", [])
            if not isinstance(style_metadata, list):
                style_metadata = []
            for item in style_metadata:
                if not isinstance(item, dict):
                    continue
                try:
                    style = VoiceStyleProfile(
                        style_profile_id=str(item["style_profile_id"]), revision=int(item.get("revision", 1)),
                        name=str(item["name"]), provider_id=service.service_id,
                        instruction=str(item["instruction"]), tags=tuple(str(tag) for tag in item.get("tags", [])),
                        status=str(item.get("status", "active")),
                    )
                except (KeyError, TypeError, ValueError):
                    continue
                styles.append(style.to_dict())
            if service.enabled:
                capabilities.append({"provider_id": service.service_id, "adapter_type": service.adapter_type,
                                     "model_id": service.model, "capability": "speech.synthesize",
                                     "configured": self._registry.has_required_secrets(service)})
        profile_candidates.extend((0, profile) for profile in self.profiles())
        styles.extend(self.styles())
        return {"profiles": self._deduplicate_profiles(profile_candidates), "styles": styles, "capabilities": capabilities}
