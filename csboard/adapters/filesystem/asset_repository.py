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
import uuid
from pathlib import Path

from csboard.application.context import utc_now
from csboard.domain.asset_ref import AssetRef
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.style_template import StyleTemplate
from csboard.domain.voice_asset import VoiceAsset


class FilesystemAssetRepository:
    """文件系统资产仓储。"""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._assets_dir = data_dir / "assets"
        self._styles_dir = self._assets_dir / "styles"
        self._blobs_dir = self._assets_dir / "blobs"
        self._voices_dir = self._assets_dir / "voices"
        self._styles_dir.mkdir(parents=True, exist_ok=True)
        self._blobs_dir.mkdir(parents=True, exist_ok=True)
        self._voices_dir.mkdir(parents=True, exist_ok=True)

    # ── StyleTemplate ──────────────────────────────────────────────

    def _styles_path(self) -> Path:
        return self._styles_dir / "styles.json"

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

    def save_style_template(self, template: StyleTemplate) -> None:
        styles = self._load_styles()
        now = utc_now()
        found = False
        for i, s in enumerate(styles):
            if s.get("style_id") == template.style_id:
                existing = StyleTemplate.from_dict(s)
                if existing.kind == "preset":
                    raise DomainError("VALIDATION_ERROR", "preset 风格禁止修改")
                template.revision = existing.revision + 1
                template.updated_at = now
                styles[i] = template.to_dict()
                found = True
                break
        if not found:
            if template.kind == "preset":
                raise DomainError("VALIDATION_ERROR", "preset 风格禁止修改")
            template.created_at = now
            template.updated_at = now
            template.revision = 1
            styles.append(template.to_dict())
        self._save_styles(styles)

    def activate_style_template(self, style_id: str) -> None:
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
        styles = self._load_styles()
        for i, s in enumerate(styles):
            if s.get("style_id") == style_id:
                if s.get("kind") == "preset":
                    raise DomainError("VALIDATION_ERROR", "preset 风格禁止停用")
                s["status"] = "inactive"
                s["updated_at"] = utc_now()
                s["revision"] = s.get("revision", 1) + 1
                styles[i] = s
                self._save_styles(styles)
                return
        raise NotFoundError("风格模板不存在")

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

    def save_asset(self, file_bytes: bytes, original_name: str, mime_type: str) -> AssetRef:
        safe_name = self._validate_safe_path(original_name)
        asset_id = self._compute_hash(file_bytes)
        blob_path = self._blob_path(asset_id)

        if blob_path.exists():
            return self.get_asset(asset_id)

        blob_path.parent.mkdir(parents=True, exist_ok=True)
        blob_path.write_bytes(file_bytes)

        now = utc_now()
        return AssetRef(
            asset_id=asset_id,
            original_name=safe_name,
            mime_type=mime_type,
            size_bytes=len(file_bytes),
            storage_path=f"assets/blobs/{asset_id[:2]}/{asset_id}",
            created_at=now,
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
    ) -> VoiceAsset:
        voice_id = uuid.uuid4().hex[:16]
        sha256 = self._compute_hash(file_bytes)
        now = utc_now()

        voice_dir = self._voice_dir(voice_id)
        voice_dir.mkdir(parents=True, exist_ok=True)

        data_path = self._voice_data_path(voice_id, audio_format)
        data_path.write_bytes(file_bytes)

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
        )

        meta_path = self._voice_meta_path(voice_id)
        meta_path.write_text(json.dumps(asset.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

        return asset

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
        meta_path = self._voice_meta_path(voice_id)
        if not meta_path.exists():
            raise NotFoundError("语音资产不存在")
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            data["is_active"] = True
            meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            raise NotFoundError("语音资产元数据损坏")

    def deactivate_voice_asset(self, voice_id: str) -> None:
        meta_path = self._voice_meta_path(voice_id)
        if not meta_path.exists():
            raise NotFoundError("语音资产不存在")
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            data["is_active"] = False
            meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            raise NotFoundError("语音资产元数据损坏")

    def update_voice_meta(
        self,
        voice_id: str,
        name: str | None = None,
        tags: list[str] | None = None,
    ) -> VoiceAsset:
        """更新音色资产的 name / tags / revision / updated_at。Router 不调用私有方法。"""
        meta_path = self._voice_meta_path(voice_id)
        if not meta_path.exists():
            raise NotFoundError("语音资产不存在")
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raise NotFoundError("语音资产元数据损坏")

        if name is not None:
            data["name"] = name
        if tags is not None:
            data["tags"] = tags
        data["revision"] = data.get("revision", 1) + 1
        data["updated_at"] = utc_now()

        tmp = meta_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(meta_path)

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
        )

        meta_path = self._voice_meta_path(voice_id)
        meta_path.write_text(json.dumps(asset.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

        return asset
