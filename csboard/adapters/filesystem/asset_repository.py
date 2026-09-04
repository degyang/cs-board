"""FilesystemAssetRepository — 文件系统资产仓储实现。

目录结构：
DATA_DIR/
  assets/
    styles/
      styles.json        # StyleTemplate 列表
    blobs/
      {asset_id[:2]}/
        {asset_id}        # 原始文件内容
    voices/
      {voice_id[:2]}/
        {voice_id}.json   # VoiceAsset 元数据
        {voice_id}.wav    # 音频文件
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import uuid
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Iterator

from csboard.application.context import utc_now
from csboard.domain.asset_ref import AssetRef
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.precondition import Precondition
from csboard.domain.style_template import StyleTemplate
from csboard.domain.voice_asset import VoiceAsset


_LOCKS_GUARD = threading.Lock()
_REPOSITORY_LOCKS: dict[str, threading.RLock] = {}
_BLOB_LINKS_GUARD = threading.Lock()
_BLOB_LINK_SOURCES: dict[tuple[int, str], Path] = {}
_SOURCE_DIGESTS: dict[tuple[str, int, int], str] = {}


def _repository_lock(data_dir: Path) -> threading.RLock:
    """Share one mutation lock across repository instances for the same data dir."""
    key = str(data_dir.resolve())
    with _LOCKS_GUARD:
        return _REPOSITORY_LOCKS.setdefault(key, threading.RLock())


class FilesystemAssetRepository:
    """文件系统资产仓储。"""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._lock = _repository_lock(data_dir)
        self._assets_dir = data_dir / "assets"
        self._styles_dir = self._assets_dir / "styles"
        self._preconditions_dir = self._assets_dir / "preconditions"
        self._blobs_dir = self._assets_dir / "blobs"
        self._voices_dir = self._assets_dir / "voices"
        self._styles_dir.mkdir(parents=True, exist_ok=True)
        self._preconditions_dir.mkdir(parents=True, exist_ok=True)
        self._blobs_dir.mkdir(parents=True, exist_ok=True)
        self._voices_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _mutation_lock(self) -> Iterator[None]:
        """Serialize read-modify-write transactions across instances and processes."""
        with self._lock:
            lock_path = self._assets_dir / ".repository.lock"
            with lock_path.open("a+b") as lock_file:
                try:
                    import fcntl
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                except ImportError:  # pragma: no cover - Windows uses the process lock above.
                    fcntl = None
                try:
                    yield
                finally:
                    if fcntl is not None:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    # ── StyleTemplate ──────────────────────────────────────────────

    def _styles_path(self) -> Path:
        return self._styles_dir / "styles.json"

    @staticmethod
    def validate_voice_metadata(metadata: dict) -> dict:
        """Keep CLI-originated voice metadata within the same persisted contract."""
        emotion_modes = {"speaker", "reference_audio", "vector", "text"}
        availability_statuses = {"available", "verified", "limited"}
        for field in ("language", "emotion_mode", "example_text", "availability_status", "status_note", "engine", "emotion_reference_asset_id", "source"):
            if field in metadata and not isinstance(metadata[field], str):
                raise DomainError("VALIDATION_ERROR", f"{field} 必须是字符串")
        if "emotion_weight" in metadata and metadata["emotion_weight"] is not None:
            weight = metadata["emotion_weight"]
            if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not 0 <= weight <= 1:
                raise DomainError("VALIDATION_ERROR", "emotion_weight 必须在 0 到 1 之间")
        if not str(metadata.get("language", "x")).strip() or not str(metadata.get("engine", "x")).strip():
            raise DomainError("VALIDATION_ERROR", "language 和 engine 不能为空")
        if "emotion_mode" in metadata and metadata["emotion_mode"] not in emotion_modes:
            raise DomainError("VALIDATION_ERROR", "emotion_mode 无效")
        if "availability_status" in metadata and metadata["availability_status"] not in availability_statuses:
            raise DomainError("VALIDATION_ERROR", "availability_status 无效")
        compatibility = metadata.get("compatibility")
        if compatibility is not None:
            if not isinstance(compatibility, dict) or not compatibility:
                raise DomainError("VALIDATION_ERROR", "compatibility 必须是非空对象")
            engines = compatibility.get("engines")
            modes = compatibility.get("emotion_modes")
            limitations = compatibility.get("limitations", [])
            if (not isinstance(engines, list) or not engines or not all(isinstance(v, str) and v for v in engines)
                    or not isinstance(modes, list) or not modes or not all(v in emotion_modes for v in modes)
                    or not isinstance(limitations, list) or not all(isinstance(v, str) for v in limitations)):
                raise DomainError("VALIDATION_ERROR", "compatibility 字段无效")
        return metadata

    def _load_styles(self) -> list[dict]:
        path = self._styles_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_styles(self, styles: list[dict]) -> None:
        path = self._styles_path()
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(styles, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def list_style_templates(
        self,
        kind: str | None = None,
        status: str | None = None,
        engine: str | None = None,
        q: str | None = None,
    ) -> list[StyleTemplate]:
        styles = self._load_styles()
        result = []
        for s in styles:
            if kind and s.get("kind") != kind:
                continue
            status_filter = status or "active"
            if s.get("status", "active") != status_filter:
                continue
            if engine and s.get("engine") != engine:
                continue
            if q and q.lower() not in s.get("name", "").lower():
                continue
            result.append(StyleTemplate.from_dict(s))
        return result

    def get_style_template(self, style_id: str) -> StyleTemplate:
        styles = self._load_styles()
        for s in styles:
            if s.get("style_id") == style_id:
                return StyleTemplate.from_dict(s)
        raise NotFoundError("风格模板不存在")

    def save_style_template(self, template: StyleTemplate, expected_revision: int | None = None) -> None:
        with self._mutation_lock():
            styles = self._load_styles()
            now = utc_now()
            found = False
            for i, s in enumerate(styles):
                if s.get("style_id") == template.style_id:
                    existing = StyleTemplate.from_dict(s)
                    if expected_revision is not None and expected_revision != existing.revision:
                        raise DomainError("REVISION_CONFLICT", "风格模板已被其他更新修改")
                    template.revision = existing.revision + 1
                    template.created_at = existing.created_at
                    template.updated_at = now
                    styles[i] = template.to_dict()
                    found = True
                    break
            if not found:
                template.created_at = now
                template.updated_at = now
                template.revision = 1
                styles.append(template.to_dict())
            self._save_styles(styles)

    def install_style_template_if_missing(self, template: StyleTemplate) -> bool:
        """Install a built-in template once, including inactive/soft-deleted entries."""
        with self._mutation_lock():
            styles = self._load_styles()
            if any(item.get("style_id") == template.style_id for item in styles):
                return False
            styles.append(template.to_dict())
            self._save_styles(styles)
            return True

    def install_style_reference_routing_if_missing(self, style_id: str, routing: dict) -> bool:
        """Add the built-in routing contract once without reviving or overwriting user edits.

        An explicitly stored empty routing object means the user disabled/cleared the
        feature and must therefore be preserved on later starts.
        """
        normalized = self.validate_style_config({"reference_routing": routing})["reference_routing"]
        with self._mutation_lock():
            styles = self._load_styles()
            for index, raw in enumerate(styles):
                if raw.get("style_id") != style_id:
                    continue
                config = dict(raw.get("config") or {})
                if "reference_routing" in config:
                    return False
                config["reference_routing"] = normalized
                raw["config"] = config
                raw["revision"] = int(raw.get("revision", 1)) + 1
                raw["updated_at"] = utc_now()
                styles[index] = raw
                self._save_styles(styles)
                return True
        raise NotFoundError("风格模板不存在")

    def validate_style_config(self, raw: object) -> dict:
        """Validate structured style configuration and referenced image assets."""
        if not isinstance(raw, dict):
            raise DomainError("VALIDATION_ERROR", "config 必须是对象")
        config = deepcopy(raw)
        if "reference_routing" not in config:
            return config
        routing = config["reference_routing"]
        if not isinstance(routing, dict):
            raise DomainError("VALIDATION_ERROR", "reference_routing 必须是对象")
        enabled = routing.get("enabled", True)
        rules = routing.get("rules", [])
        if not isinstance(enabled, bool) or routing.get("match_mode", "first") != "first":
            raise DomainError("VALIDATION_ERROR", "参考图路由配置无效")
        if not isinstance(rules, list) or len(rules) > 32:
            raise DomainError("VALIDATION_ERROR", "参考图路由规则必须是最多 32 项的数组")
        normalized_rules: list[dict] = []
        rule_ids: set[str] = set()
        for order, item in enumerate(rules, 1):
            if not isinstance(item, dict):
                raise DomainError("VALIDATION_ERROR", "参考图路由规则必须是对象")
            rule_id = item.get("rule_id")
            name = item.get("name")
            keywords = item.get("keywords")
            asset_ids = item.get("reference_asset_ids")
            if not isinstance(rule_id, str) or not rule_id.strip() or rule_id in rule_ids:
                raise DomainError("VALIDATION_ERROR", "参考图路由 rule_id 必须非空且唯一")
            if not isinstance(name, str) or not name.strip() or len(name.strip()) > 40:
                raise DomainError("VALIDATION_ERROR", "参考图路由名称必须为 1–40 个字符")
            if (not isinstance(keywords, list) or not keywords or len(keywords) > 32
                    or not all(isinstance(keyword, str) and keyword.strip() and len(keyword.strip()) <= 40 for keyword in keywords)):
                raise DomainError("VALIDATION_ERROR", "每条参考图路由必须包含 1–32 个有效关键字")
            normalized_keywords = list(dict.fromkeys(keyword.strip() for keyword in keywords))
            if not isinstance(asset_ids, list) or not 1 <= len(asset_ids) <= 3:
                raise DomainError("VALIDATION_ERROR", "每条参考图路由必须包含 1–3 张参考图片")
            normalized_asset_ids = list(dict.fromkeys(asset_ids))
            if len(normalized_asset_ids) != len(asset_ids) or not all(isinstance(asset_id, str) and asset_id for asset_id in asset_ids):
                raise DomainError("VALIDATION_ERROR", "参考图片 asset_id 必须有效且不能重复")
            for asset_id in normalized_asset_ids:
                try:
                    self.get_asset(asset_id)
                    content = self.read_asset_bytes(asset_id)
                except NotFoundError as exc:
                    raise DomainError("VALIDATION_ERROR", "参考图路由图片不存在或不可读取") from exc
                if not self._is_image_blob(content):
                    raise DomainError("VALIDATION_ERROR", "参考图路由只能引用图片资产")
            rule_ids.add(rule_id)
            normalized_rules.append({
                "rule_id": rule_id.strip(), "name": name.strip(),
                "keywords": normalized_keywords,
                "reference_asset_ids": normalized_asset_ids, "order": order,
            })
        config["reference_routing"] = {
            "enabled": enabled and bool(normalized_rules),
            "match_mode": "first",
            "rules": normalized_rules,
        }
        return config

    def validate_style_characters(self, raw: object) -> list[dict]:
        """Validate revision-owned character references against readable image blobs."""
        if not isinstance(raw, list):
            raise DomainError("VALIDATION_ERROR", "characters 必须是数组")
        characters: list[dict] = []
        character_ids: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                raise DomainError("VALIDATION_ERROR", "characters 成员必须是对象")
            character_id = item.get("character_id")
            name = item.get("name")
            description = item.get("description")
            reference_asset_ids = item.get("reference_asset_ids")
            if not isinstance(character_id, str) or not character_id.strip():
                raise DomainError("VALIDATION_ERROR", "character_id 不能为空")
            if character_id in character_ids:
                raise DomainError("VALIDATION_ERROR", "character_id 必须唯一")
            if not isinstance(name, str) or not name.strip() or not isinstance(description, str):
                raise DomainError("VALIDATION_ERROR", "character name 和 description 必须是有效文本")
            if not isinstance(reference_asset_ids, list) or not 1 <= len(reference_asset_ids) <= 3:
                raise DomainError("VALIDATION_ERROR", "每个人物必须有 1–3 张参考图")
            if len(reference_asset_ids) != len(set(reference_asset_ids)):
                raise DomainError("VALIDATION_ERROR", "人物参考图不能重复")
            for asset_id in reference_asset_ids:
                if not isinstance(asset_id, str) or not asset_id:
                    raise DomainError("VALIDATION_ERROR", "reference_asset_ids 必须是资产 ID")
                try:
                    self.get_asset(asset_id)
                    content = self.read_asset_bytes(asset_id)
                except NotFoundError as exc:
                    raise DomainError("VALIDATION_ERROR", "人物参考图资产不存在或不可读取") from exc
                if not self._is_image_blob(content):
                    raise DomainError("VALIDATION_ERROR", "人物参考图必须是图片资产")
            character_ids.add(character_id)
            characters.append({"character_id": character_id, "name": name, "description": description,
                               "reference_asset_ids": list(reference_asset_ids)})
        return characters

    def activate_style_template(self, style_id: str) -> None:
        with self._mutation_lock():
            styles = self._load_styles()
            for i, s in enumerate(styles):
                if s.get("style_id") == style_id:
                    s["status"] = "active"
                    s["updated_at"] = utc_now()
                    s["revision"] = s.get("revision", 1) + 1
                    styles[i] = s
                    self._save_styles(styles)
                    return
        raise NotFoundError("风格模板不存在")

    def deactivate_style_template(self, style_id: str) -> None:
        with self._mutation_lock():
            styles = self._load_styles()
            for i, s in enumerate(styles):
                if s.get("style_id") == style_id:
                    s["status"] = "inactive"
                    s["updated_at"] = utc_now()
                    s["revision"] = s.get("revision", 1) + 1
                    styles[i] = s
                    self._save_styles(styles)
                    return
        raise NotFoundError("风格模板不存在")

    # ── Precondition ──────────────────────────────────────────────

    def _preconditions_path(self) -> Path:
        return self._preconditions_dir / "preconditions.json"

    def _load_preconditions(self) -> list[dict]:
        path = self._preconditions_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def list_preconditions(self) -> list[Precondition]:
        result: list[Precondition] = []
        for item in self._load_preconditions():
            try:
                result.append(Precondition.from_dict(item))
            except (KeyError, TypeError, ValueError):
                continue
        return result

    def get_precondition(self, precondition_id: str) -> Precondition:
        for item in self._load_preconditions():
            if item.get("precondition_id") == precondition_id:
                try:
                    return Precondition.from_dict(item)
                except (KeyError, TypeError, ValueError) as exc:
                    raise NotFoundError("前置条件资产元数据损坏") from exc
        raise NotFoundError("前置条件资产不存在")

    # ── AssetRef ───────────────────────────────────────────────────

    def _validate_safe_path(self, name: str) -> str:
        if ".." in name or "/" in name or "\\" in name:
            raise DomainError("VALIDATION_ERROR", "文件名包含非法字符")
        if name.startswith("/") or (len(name) >= 2 and name[1] == ":"):
            raise DomainError("VALIDATION_ERROR", "文件名包含非法字符")
        return name

    def _compute_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _blob_path(self, asset_id: str) -> Path:
        return self._blobs_dir / asset_id[:2] / asset_id

    @staticmethod
    def _is_image_blob(content: bytes) -> bool:
        return (content.startswith(b"\x89PNG\r\n\x1a\n") or content.startswith(b"\xff\xd8\xff")
                or content.startswith((b"GIF87a", b"GIF89a"))
                or (content.startswith(b"RIFF") and content[8:12] == b"WEBP"))

    def save_asset(self, file_bytes: bytes, original_name: str, mime_type: str) -> AssetRef:
        safe_name = self._validate_safe_path(original_name)
        asset_id = self._compute_hash(file_bytes)
        blob_path = self._blob_path(asset_id)
        with self._mutation_lock():
            if blob_path.exists():
                return self.get_asset(asset_id)
            blob_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = blob_path.with_name(f"{blob_path.name}.tmp")
            tmp.write_bytes(file_bytes)
            tmp.replace(blob_path)

        now = utc_now()
        return AssetRef(
            asset_id=asset_id,
            original_name=safe_name,
            mime_type=mime_type,
            size_bytes=len(file_bytes),
            storage_path=f"assets/blobs/{asset_id[:2]}/{asset_id}",
            created_at=now,
        )

    def save_asset_from_file(self, source: Path, original_name: str, mime_type: str) -> AssetRef:
        """Install an immutable file without repeatedly copying identical seed blobs.

        Content identity and the repository layout remain exactly the same as
        ``save_asset``.  After the first copy on a filesystem, later repositories
        may hard-link the already verified immutable blob; unavailable/cross-device
        links safely fall back to a normal copy.
        """
        safe_name = self._validate_safe_path(original_name)
        source_stat = source.stat()
        source_key = (str(source.resolve()), source_stat.st_size, source_stat.st_mtime_ns)
        with _BLOB_LINKS_GUARD:
            asset_id = _SOURCE_DIGESTS.get(source_key)
        if asset_id is None:
            digest = hashlib.sha256()
            with source.open("rb") as input_file:
                for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
                    digest.update(chunk)
            asset_id = digest.hexdigest()
            with _BLOB_LINKS_GUARD:
                _SOURCE_DIGESTS[source_key] = asset_id
        blob_path = self._blob_path(asset_id)
        with self._mutation_lock():
            if blob_path.exists():
                return self.get_asset(asset_id)
            blob_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = blob_path.with_name(f"{blob_path.name}.tmp")
            device = blob_path.parent.stat().st_dev
            link_source: Path | None = source if source.stat().st_dev == device else None
            with _BLOB_LINKS_GUARD:
                cached = _BLOB_LINK_SOURCES.get((device, asset_id))
                if cached is not None and cached.is_file():
                    link_source = cached
            try:
                if link_source is None:
                    raise OSError("no same-filesystem blob source")
                os.link(link_source, tmp)
            except OSError:
                shutil.copyfile(source, tmp)
            tmp.replace(blob_path)
            with _BLOB_LINKS_GUARD:
                _BLOB_LINK_SOURCES[(device, asset_id)] = blob_path

        stat = blob_path.stat()
        return AssetRef(
            asset_id=asset_id,
            original_name=safe_name,
            mime_type=mime_type,
            size_bytes=stat.st_size,
            storage_path=f"assets/blobs/{asset_id[:2]}/{asset_id}",
            created_at=utc_now(),
        )

    def get_asset(self, asset_id: str) -> AssetRef:
        blob_path = self._blob_path(asset_id)
        if not blob_path.exists():
            raise NotFoundError("资产不存在")
        stat = blob_path.stat()
        return AssetRef(
            asset_id=asset_id,
            original_name=blob_path.name,
            mime_type="application/octet-stream",
            size_bytes=stat.st_size,
            storage_path=f"assets/blobs/{asset_id[:2]}/{asset_id}",
            created_at=utc_now(),
        )

    def read_asset_bytes(self, asset_id: str) -> bytes:
        blob_path = self._blob_path(asset_id)
        try:
            resolved = blob_path.resolve()
            blobs_resolved = self._blobs_dir.resolve()
            if not str(resolved).startswith(str(blobs_resolved)):
                raise DomainError("VALIDATION_ERROR", "路径逃逸检测")
        except (OSError, ValueError):
            raise DomainError("VALIDATION_ERROR", "路径逃逸检测")
        if not blob_path.exists():
            raise NotFoundError("资产不存在")
        return blob_path.read_bytes()

    # ── VoiceAsset ─────────────────────────────────────────────────

    def _voice_dir(self, voice_id: str) -> Path:
        return self._voices_dir / voice_id[:2]

    def _voice_meta_path(self, voice_id: str) -> Path:
        return self._voice_dir(voice_id) / f"{voice_id}.json"

    def _voice_data_path(self, voice_id: str, audio_format: str) -> Path:
        return self._voice_dir(voice_id) / f"{voice_id}.{audio_format}"

    def _load_all_voices(self) -> list[dict]:
        result = []
        for meta_path in self._voices_dir.glob("*/*.json"):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                result.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        return result

    def create_voice_asset(
        self,
        name: str,
        duration_ms: int,
        sample_rate: int,
        channels: int,
        audio_format: str,
    ) -> VoiceAsset:
        """创建语音元数据（无文件内容）。"""
        voice_id = uuid.uuid4().hex[:16]
        now = utc_now()

        voice_dir = self._voice_dir(voice_id)
        voice_dir.mkdir(parents=True, exist_ok=True)

        asset = VoiceAsset(
            voice_id=voice_id,
            name=name,
            storage_path=f"assets/voices/{voice_id[:2]}/{voice_id}.{audio_format}",
            duration_ms=duration_ms,
            sample_rate=sample_rate,
            channels=channels,
            format=audio_format,
            sha256="",
            created_at=now,
        )

        meta_path = self._voice_meta_path(voice_id)
        meta_path.write_text(json.dumps(asset.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

        return asset

    def save_voice_asset(
        self,
        file_bytes: bytes,
        name: str,
        duration_ms: int,
        sample_rate: int,
        channels: int,
        audio_format: str,
        metadata: dict | None = None,
    ) -> VoiceAsset:
        voice_id = uuid.uuid4().hex[:16]
        return self._write_new_voice(
            voice_id, file_bytes, name, duration_ms, sample_rate, channels,
            audio_format, metadata=metadata,
        )

    def _write_new_voice(
        self,
        voice_id: str,
        file_bytes: bytes,
        name: str,
        duration_ms: int,
        sample_rate: int,
        channels: int,
        audio_format: str,
        metadata: dict | None = None,
        created_at: str | None = None,
    ) -> VoiceAsset:
        """Write a new voice and metadata atomically while the caller owns identity."""
        sha256 = self._compute_hash(file_bytes)
        now = created_at or utc_now()
        voice_dir = self._voice_dir(voice_id)
        voice_dir.mkdir(parents=True, exist_ok=True)
        data_path = self._voice_data_path(voice_id, audio_format)
        data_tmp = data_path.with_suffix(f".{audio_format}.tmp")
        data_tmp.write_bytes(file_bytes)
        data_tmp.replace(data_path)
        asset = VoiceAsset(
            voice_id=voice_id,
            name=name,
            storage_path=f"assets/voices/{voice_id[:2]}/{voice_id}.{audio_format}",
            duration_ms=duration_ms,
            sample_rate=sample_rate,
            channels=channels,
            format=audio_format,
            sha256=sha256,
            created_at=now,
            updated_at=now,
            **(metadata or {}),
        )
        meta_path = self._voice_meta_path(voice_id)
        meta_tmp = meta_path.with_suffix(".json.tmp")
        meta_tmp.write_text(json.dumps(asset.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        meta_tmp.replace(meta_path)
        return asset

    def install_voice_asset_if_missing(
        self,
        voice_id: str,
        file_bytes: bytes,
        name: str,
        duration_ms: int,
        sample_rate: int,
        channels: int,
        metadata: dict,
    ) -> bool:
        """Install a stable built-in voice once without reviving or overwriting it."""
        with self._mutation_lock():
            meta_path = self._voice_meta_path(voice_id)
            if meta_path.exists():
                return False
            self.validate_voice_metadata(metadata)
            self._write_new_voice(
                voice_id, file_bytes, name, duration_ms, sample_rate, channels,
                "wav", metadata=metadata, created_at="2026-08-31T00:00:00Z",
            )
            return True

    def get_voice_asset(self, voice_id: str) -> VoiceAsset:
        meta_path = self._voice_meta_path(voice_id)
        if not meta_path.exists():
            raise NotFoundError("语音资产不存在")
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            return VoiceAsset.from_dict(data)
        except (json.JSONDecodeError, OSError):
            raise NotFoundError("语音资产元数据损坏")

    def list_voice_assets(self) -> list[VoiceAsset]:
        result = []
        for data in self._load_all_voices():
            try:
                asset = VoiceAsset.from_dict(data)
                if asset.is_active:
                    result.append(asset)
            except (KeyError, ValueError):
                continue
        return result

    def get_voice_content(self, voice_id: str) -> bytes:
        voice = self.get_voice_asset(voice_id)
        data_path = self._voice_data_path(voice_id, voice.format)
        if not data_path.exists():
            raise NotFoundError("语音内容不存在")
        return data_path.read_bytes()

    def activate_voice_asset(self, voice_id: str) -> None:
        with self._mutation_lock():
            meta_path = self._voice_meta_path(voice_id)
            if not meta_path.exists():
                raise NotFoundError("语音资产不存在")
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                data["is_active"] = True
                data["revision"] = data.get("revision", 1) + 1
                data["updated_at"] = utc_now()
                self._write_voice_metadata(meta_path, data)
            except (json.JSONDecodeError, OSError):
                raise NotFoundError("语音资产元数据损坏")

    def deactivate_voice_asset(self, voice_id: str) -> None:
        with self._mutation_lock():
            meta_path = self._voice_meta_path(voice_id)
            if not meta_path.exists():
                raise NotFoundError("语音资产不存在")
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                data["is_active"] = False
                data["revision"] = data.get("revision", 1) + 1
                data["updated_at"] = utc_now()
                self._write_voice_metadata(meta_path, data)
            except (json.JSONDecodeError, OSError):
                raise NotFoundError("语音资产元数据损坏")

    @staticmethod
    def _write_voice_metadata(meta_path: Path, data: dict) -> None:
        tmp = meta_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(meta_path)

    def update_voice_meta(
        self,
        voice_id: str,
        name: str | None = None,
        tags: list[str] | None = None,
        metadata: dict | None = None,
        expected_revision: int | None = None,
    ) -> VoiceAsset:
        """更新音色资产的 name / tags / revision / updated_at。Router 不调用私有方法。"""
        with self._mutation_lock():
            meta_path = self._voice_meta_path(voice_id)
            if not meta_path.exists():
                raise NotFoundError("语音资产不存在")
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                raise NotFoundError("语音资产元数据损坏")
            current_revision = data.get("revision", 1)
            if expected_revision is not None and expected_revision != current_revision:
                raise DomainError("REVISION_CONFLICT", "音色资产已被其他更新修改")
            if name is not None:
                data["name"] = name
            if tags is not None:
                data["tags"] = tags
            if metadata:
                data.update(metadata)
            data["revision"] = current_revision + 1
            data["updated_at"] = utc_now()
            self._write_voice_metadata(meta_path, data)
            return VoiceAsset.from_dict(data)

    def save_voice_from_temp(
        self,
        temp_path: Path,
        name: str,
        tags: list[str],
        duration_ms: int,
        sample_rate: int,
        channels: int,
        audio_format: str,
        metadata: dict | None = None,
    ) -> VoiceAsset:
        """从临时文件保存音色：计算 sha256，原子写入，清理临时文件。"""
        import shutil

        voice_id = uuid.uuid4().hex[:16]
        now = utc_now()

        voice_dir = self._voice_dir(voice_id)
        voice_dir.mkdir(parents=True, exist_ok=True)

        data_path = self._voice_data_path(voice_id, audio_format)

        # 计算 sha256
        sha256_hash = hashlib.sha256()
        with temp_path.open("rb") as f:
            while chunk := f.read(8192):
                sha256_hash.update(chunk)

        # 原子写入
        try:
            shutil.move(str(temp_path), str(data_path))
        except Exception:
            # fallback: copy then delete
            shutil.copy2(str(temp_path), str(data_path))
            temp_path.unlink(missing_ok=True)

        asset = VoiceAsset(
            voice_id=voice_id,
            name=name,
            storage_path=f"assets/voices/{voice_id[:2]}/{voice_id}.{audio_format}",
            duration_ms=duration_ms,
            sample_rate=sample_rate,
            channels=channels,
            format=audio_format,
            sha256=sha256_hash.hexdigest(),
            created_at=now,
            updated_at=now,
            tags=tags,
            revision=1,
            **(metadata or {}),
        )

        meta_path = self._voice_meta_path(voice_id)
        meta_path.write_text(json.dumps(asset.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

        return asset
