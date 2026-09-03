"""Mountain Asset API — /api/v1/assets 路由。

音色 multipart 上传、真实媒体元数据、Range 支持。
Style 列表支持 kind/status/engine/q/cursor/limit。
preset 禁止 PATCH、DELETE、activate、deactivate。
通用上传流式写入临时文件。
Router 不调用 Repository 私有方法。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response

from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
from csboard.application.context import utc_now
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.style_template import StyleTemplate
from webapp.error_contract import domain_error_response

ASSET_UPLOAD_MAX_BYTES = 100 * 1024 * 1024  # 100 MB
VOICE_UPLOAD_MAX_BYTES = 50 * 1024 * 1024  # 50 MB

# 允许的音频格式
VOICE_ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}
VOICE_ALLOWED_MIMES = {
    "audio/wav", "audio/x-wav", "audio/wave",
    "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/ogg",
    "audio/flac", "audio/x-flac",
}


def _probe_audio_metadata(file_path: Path) -> dict[str, Any]:
    """使用 ffprobe 获取音频元数据。"""
    import subprocess
    import shutil

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        # 回退：默认值
        return {"duration_ms": 0, "sample_rate": 0, "channels": 0, "format": "wav"}

    try:
        result = subprocess.run(
            [
                ffprobe, "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", str(file_path),
            ],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return {"duration_ms": 0, "sample_rate": 0, "channels": 0, "format": "wav"}

        data = json.loads(result.stdout)
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

        duration_ms = int(float(fmt.get("duration", 0)) * 1000)
        sample_rate = int(audio_stream.get("sample_rate", 0))
        channels = int(audio_stream.get("channels", 0))
        format_name = fmt.get("format_name", "wav")
        # 简化格式名
        if "wav" in format_name:
            audio_format = "wav"
        elif "mp3" in format_name:
            audio_format = "mp3"
        elif "ogg" in format_name:
            audio_format = "ogg"
        elif "flac" in format_name:
            audio_format = "flac"
        elif "m4a" in format_name or "mov" in format_name or "mp4" in format_name:
            audio_format = "m4a"
        else:
            audio_format = "wav"

        return {
            "duration_ms": duration_ms,
            "sample_rate": sample_rate,
            "channels": channels,
            "format": audio_format,
        }
    except Exception:
        return {"duration_ms": 0, "sample_rate": 0, "channels": 0, "format": "wav"}


def _is_preset(repository: FilesystemAssetRepository, style_id: str) -> bool:
    """检查是否为 preset 风格。"""
    try:
        template = repository.get_style_template(style_id)
        return template.kind == "preset"
    except NotFoundError:
        return False


def mountain_asset_router(
    data_dir: Path,
    repository: FilesystemAssetRepository | None = None,
) -> APIRouter:
    router = APIRouter()
    repository = repository or FilesystemAssetRepository(data_dir)

    # ── styles ────────────────────────────────────────────────────

    @router.get("/api/v1/assets/styles")
    def list_styles(
        kind: str | None = None,
        status: str | None = None,
        engine: str | None = None,
        q: str | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ):
        templates = repository.list_style_templates(kind=kind, status=status, engine=engine, q=q)
        # 分页
        if cursor:
            cursor_idx = -1
            for idx, t in enumerate(templates):
                if t.style_id == cursor:
                    cursor_idx = idx + 1
                    break
            if cursor_idx > 0:
                templates = templates[cursor_idx:]
        effective_limit = max(1, min(limit, 100))
        page = templates[:effective_limit]
        next_cursor = page[-1].style_id if len(page) >= effective_limit and len(templates) > effective_limit else None
        return {"items": [t.to_dict() for t in page], "total": len(templates), "next_cursor": next_cursor}

    @router.post("/api/v1/assets/styles")
    def create_style(request: Request, payload: dict[str, Any]):
        name = payload.get("name")
        prompt_text = payload.get("prompt_text")
        if not name or not prompt_text:
            return domain_error_response(DomainError("VALIDATION_ERROR", "name 和 prompt_text 不能为空"), status_code=400)

        kind = payload.get("kind", "custom")
        engine = payload.get("engine", "whiteboard")
        description = payload.get("description", "")
        negative_prompt = payload.get("negative_prompt", "")
        preview_asset_id = payload.get("preview_asset_id", "")
        config = payload.get("config", {})
        if not isinstance(config, dict):
            return domain_error_response(DomainError("VALIDATION_ERROR", "config 必须是对象"), status_code=400)

        raw_tags = payload.get("tags", [])
        if not isinstance(raw_tags, list):
            return domain_error_response(DomainError("VALIDATION_ERROR", "tags 必须是数组"), status_code=400)

        now = utc_now()
        template = StyleTemplate(
            style_id=uuid.uuid4().hex[:16],
            revision=1,
            name=name,
            kind=kind,
            prompt_text=prompt_text,
            engine=engine,
            description=description,
            negative_prompt=negative_prompt,
            tags=raw_tags,
            preview_asset_id=preview_asset_id,
            status="active",
            created_at=now,
            updated_at=now,
            config=config,
        )
        repository.save_style_template(template)
        return template.to_dict()

    @router.get("/api/v1/assets/styles/{style_id}")
    def get_style(style_id: str):
        try:
            template = repository.get_style_template(style_id)
            return template.to_dict()
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.patch("/api/v1/assets/styles/{style_id}")
    def patch_style(style_id: str, payload: dict[str, Any]):
        try:
            template = repository.get_style_template(style_id)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

        # preset 禁止修改
        if template.kind == "preset":
            return domain_error_response(
                DomainError("VALIDATION_ERROR", "preset 风格禁止修改"), status_code=400
            )

        if "name" in payload:
            template.name = payload["name"]
        if "prompt_text" in payload:
            template.prompt_text = payload["prompt_text"]
        if "engine" in payload:
            template.engine = payload["engine"]
        if "description" in payload:
            template.description = payload["description"]
        if "negative_prompt" in payload:
            template.negative_prompt = payload["negative_prompt"]
        if "preview_asset_id" in payload:
            template.preview_asset_id = payload["preview_asset_id"]
        if "tags" in payload:
            raw_tags = payload["tags"]
            if not isinstance(raw_tags, list):
                return domain_error_response(DomainError("VALIDATION_ERROR", "tags 必须是数组"), status_code=400)
            template.tags = raw_tags
        if "config" in payload:
            if not isinstance(payload["config"], dict):
                return domain_error_response(DomainError("VALIDATION_ERROR", "config 必须是对象"), status_code=400)
            template.config = payload["config"]
        if "expected_revision" in payload:
            template.expected_revision = payload["expected_revision"]

        try:
            repository.save_style_template(template)
            return template.to_dict()
        except DomainError as exc:
            return domain_error_response(exc, status_code=409 if exc.code == "REVISION_CONFLICT" else 400)

    @router.delete("/api/v1/assets/styles/{style_id}")
    def delete_style(style_id: str):
        try:
            template = repository.get_style_template(style_id)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

        # preset 禁止删除
        if template.kind == "preset":
            return domain_error_response(
                DomainError("VALIDATION_ERROR", "preset 风格禁止删除"), status_code=400
            )

        repository.deactivate_style_template(style_id)
        return {"ok": True}

    @router.post("/api/v1/assets/styles/{style_id}/activate")
    def activate_style(style_id: str):
        # preset 禁止 activate
        if _is_preset(repository, style_id):
            return domain_error_response(
                DomainError("VALIDATION_ERROR", "preset 风格禁止启用/停用"), status_code=400
            )
        try:
            repository.activate_style_template(style_id)
            return repository.get_style_template(style_id).to_dict()
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/assets/styles/{style_id}/deactivate")
    def deactivate_style(style_id: str):
        # preset 禁止 deactivate
        if _is_preset(repository, style_id):
            return domain_error_response(
                DomainError("VALIDATION_ERROR", "preset 风格禁止启用/停用"), status_code=400
            )
        try:
            repository.deactivate_style_template(style_id)
            return repository.get_style_template(style_id).to_dict()
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/assets/styles/{style_id}/copy")
    def copy_style(style_id: str):
        try:
            source = repository.get_style_template(style_id)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

        now = utc_now()
        custom = source.copy_to_custom(uuid.uuid4().hex[:16], now)
        repository.save_style_template(custom)
        return custom.to_dict()

    # ── uploads ───────────────────────────────────────────────────

    @router.post("/api/v1/assets/uploads")
    async def upload_asset(file: UploadFile = File(...)):
        if not file.filename:
            return domain_error_response(DomainError("VALIDATION_ERROR", "缺少文件名"), status_code=400)

        safe_name = Path(file.filename).name
        if safe_name != file.filename or ".." in file.filename:
            return domain_error_response(DomainError("VALIDATION_ERROR", "文件名不合法"), status_code=400)

        # 流式写入临时文件
        temp_fd, temp_path_str = tempfile.mkstemp(dir=str(data_dir / "temp"))
        temp_path = Path(temp_path_str)
        sha256_hash = hashlib.sha256()
        total_bytes = 0

        try:
            with os.fdopen(temp_fd, "wb") as tmp:
                while chunk := await file.read(8192):
                    total_bytes += len(chunk)
                    if total_bytes > ASSET_UPLOAD_MAX_BYTES:
                        raise HTTPException(413, "文件大小超过 100MB 限制")
                    sha256_hash.update(chunk)
                    tmp.write(chunk)

            asset = repository.save_asset(
                file_bytes=temp_path.read_bytes(),
                original_name=safe_name,
                mime_type=file.content_type or "application/octet-stream",
            )
            return asset.to_dict()
        except HTTPException:
            raise
        except Exception as exc:
            return domain_error_response(
                DomainError("UPLOAD_FAILED", f"上传失败: {exc}"), status_code=500
            )
        finally:
            temp_path.unlink(missing_ok=True)

    @router.get("/api/v1/assets/blobs/{asset_id}")
    def get_blob(asset_id: str):
        try:
            asset = repository.get_asset(asset_id)
            content = repository.read_asset_bytes(asset_id)
            return Response(
                content=content,
                media_type=asset.mime_type or "application/octet-stream",
            )
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    # ── voices ────────────────────────────────────────────────────

    @router.get("/api/v1/assets/voices")
    def list_voices():
        voices = repository.list_voice_assets()
        return {"items": [_voice_to_public(v) for v in voices], "total": len(voices), "next_cursor": None}

    @router.post("/api/v1/assets/voices")
    async def create_voice(
        file: UploadFile = File(...),
        name: str = Form(""),
        tags: str = Form(""),
    ):
        """multipart 上传音色：file、name、tags。"""
        if not file.filename:
            return domain_error_response(DomainError("VALIDATION_ERROR", "缺少音频文件"), status_code=400)

        # 解析 tags
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        # 校验扩展名
        original_name = Path(file.filename).name
        suffix = Path(original_name).suffix.lower()
        if suffix not in VOICE_ALLOWED_EXTENSIONS:
            return domain_error_response(
                DomainError("VALIDATION_ERROR", f"不支持的音频格式: {suffix}"), status_code=400
            )

        # 校验 MIME
        if file.content_type and file.content_type not in VOICE_ALLOWED_MIMES:
            return domain_error_response(
                DomainError("VALIDATION_ERROR", f"不支持的 MIME 类型: {file.content_type}"), status_code=400
            )

        # 流式写入临时文件
        temp_fd, temp_path_str = tempfile.mkstemp(dir=str(data_dir / "temp"))
        temp_path = Path(temp_path_str)
        total_bytes = 0

        try:
            with os.fdopen(temp_fd, "wb") as tmp:
                while chunk := await file.read(8192):
                    total_bytes += len(chunk)
                    if total_bytes > VOICE_UPLOAD_MAX_BYTES:
                        raise HTTPException(413, "音频文件超过 50MB 限制")
                    tmp.write(chunk)

            # 校验文件签名（WAV: RIFF, MP3: ID3 or 0xFF, OGG: OggS, FLAC: fLaC）
            with temp_path.open("rb") as f:
                header = f.read(12)
            valid_signatures = [
                b"RIFF",  # WAV
                b"ID3",   # MP3 with ID3 tag
                b"\xff\xfb",  # MP3 frame sync
                b"\xff\xf3",  # MP3 frame sync
                b"OggS",  # OGG
                b"fLaC",  # FLAC
                b"\x00\x00\x00",  # M4A/MP4 (ftyp box)
            ]
            if not any(header.startswith(sig) for sig in valid_signatures):
                temp_path.unlink(missing_ok=True)
                return domain_error_response(
                    DomainError("VALIDATION_ERROR", "文件签名不匹配，可能不是有效的音频文件"), status_code=400
                )

            # FFprobe 获取元数据
            meta = _probe_audio_metadata(temp_path)

            voice = repository.save_voice_from_temp(
                temp_path=temp_path,
                name=name or original_name,
                tags=tag_list,
                duration_ms=meta["duration_ms"],
                sample_rate=meta["sample_rate"],
                channels=meta["channels"],
                audio_format=meta["format"],
            )
            return _voice_to_public(voice)
        except HTTPException:
            raise
        except Exception as exc:
            temp_path.unlink(missing_ok=True)
            return domain_error_response(
                DomainError("UPLOAD_FAILED", f"音色上传失败: {exc}"), status_code=500
            )

    @router.get("/api/v1/assets/voices/{voice_id}")
    def get_voice(voice_id: str):
        try:
            voice = repository.get_voice_asset(voice_id)
            return _voice_to_public(voice)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.patch("/api/v1/assets/voices/{voice_id}")
    def patch_voice(voice_id: str, payload: dict[str, Any]):
        """更新 name / tags。通过 Repository 公共方法，不调用私有方法。"""
        name = payload.get("name")
        tags = payload.get("tags")
        if tags is not None and not isinstance(tags, list):
            return domain_error_response(DomainError("VALIDATION_ERROR", "tags 必须是数组"), status_code=400)
        try:
            voice = repository.update_voice_meta(voice_id, name=name, tags=tags)
            return _voice_to_public(voice)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.delete("/api/v1/assets/voices/{voice_id}")
    def delete_voice(voice_id: str):
        try:
            repository.deactivate_voice_asset(voice_id)
            return {"ok": True}
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/assets/voices/{voice_id}/activate")
    def activate_voice(voice_id: str):
        try:
            repository.activate_voice_asset(voice_id)
            return _voice_to_public(repository.get_voice_asset(voice_id))
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/assets/voices/{voice_id}/deactivate")
    def deactivate_voice(voice_id: str):
        try:
            repository.deactivate_voice_asset(voice_id)
            return _voice_to_public(repository.get_voice_asset(voice_id))
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    def _voice_to_public(voice) -> dict[str, Any]:
        """过滤 storage_path 等内部字段。"""
        d = voice.to_dict()
        d.pop("storage_path", None)
        return d

    @router.get("/api/v1/assets/voices/{voice_id}/content")
    @router.head("/api/v1/assets/voices/{voice_id}/content")
    def get_voice_content(voice_id: str, request: Request):
        """支持 HEAD、206 Range、416 Invalid Range。"""
        try:
            voice = repository.get_voice_asset(voice_id)
            content = repository.get_voice_content(voice_id)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

        media_type = f"audio/{voice.format}" if voice.format else "audio/wav"
        total_size = len(content)

        # HEAD 请求
        if request.method == "HEAD":
            return Response(
                content=b"",
                media_type=media_type,
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(total_size),
                },
            )

        range_header = request.headers.get("range")
        if range_header:
            match = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if not match:
                # 无效 Range → 416
                return Response(
                    content=b"",
                    status_code=416,
                    headers={
                        "Content-Range": f"bytes */{total_size}",
                    },
                )

            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else total_size - 1

            # 校验 Range 有效性
            if start >= total_size or end >= total_size or start > end:
                return Response(
                    content=b"",
                    status_code=416,
                    headers={
                        "Content-Range": f"bytes */{total_size}",
                    },
                )

            end = min(end, total_size - 1)
            chunk = content[start:end + 1]
            return Response(
                content=chunk,
                media_type=media_type,
                status_code=206,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{total_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(len(chunk)),
                },
            )

        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(total_size),
            },
        )

    return router
