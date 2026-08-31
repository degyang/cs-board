"""Mountain Asset API — /api/v1/assets 路由。"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response

from csboard.adapters.ffmpeg.media_adapter import FFmpegMediaAdapter
from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
from csboard.domain.asset_ref import AssetRef
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.style_template import StyleTemplate
from csboard.domain.voice_asset import VoiceAsset
from webapp.error_contract import domain_error_response

ASSET_UPLOAD_MAX_BYTES = 100 * 1024 * 1024  # 100 MB


def mountain_asset_router(data_dir: Path) -> APIRouter:
    router = APIRouter()
    repository = FilesystemAssetRepository(data_dir)

    # ── styles ────────────────────────────────────────────────────

    @router.get("/api/v1/assets/styles")
    def list_styles(kind: str | None = None, status: str | None = None, limit: int = 50):
        templates = repository.list_style_templates(kind=kind, status=status)
        return {"items": [t.to_dict() for t in templates], "total": len(templates), "next_cursor": None}

    @router.post("/api/v1/assets/styles")
    def create_style(request: Request, payload: dict[str, Any]):
        from csboard.application.context import utc_now
        import uuid

        name = payload.get("name")
        prompt_text = payload.get("prompt_text")
        if not name or not prompt_text:
            return domain_error_response(DomainError("VALIDATION_ERROR", "name 和 prompt_text 不能为空"), status_code=400)

        kind = payload.get("kind", "custom")
        engine = payload.get("engine", "whiteboard")
        description = payload.get("description", "")
        negative_prompt = payload.get("negative_prompt", "")
        preview_asset_id = payload.get("preview_asset_id", "")

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
        from csboard.application.context import utc_now

        try:
            template = repository.get_style_template(style_id)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

        if template.kind == "preset":
            return domain_error_response(DomainError("VALIDATION_ERROR", "preset 风格禁止修改"), status_code=400)

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

        repository.save_style_template(template)
        return template.to_dict()

    @router.delete("/api/v1/assets/styles/{style_id}")
    def delete_style(style_id: str):
        try:
            template = repository.get_style_template(style_id)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

        if template.kind == "preset":
            return domain_error_response(DomainError("VALIDATION_ERROR", "preset 风格禁止删除"), status_code=400)

        repository.deactivate_style_template(style_id)
        return {"ok": True}

    @router.post("/api/v1/assets/styles/{style_id}/activate")
    def activate_style(style_id: str):
        try:
            repository.activate_style_template(style_id)
            return repository.get_style_template(style_id).to_dict()
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/assets/styles/{style_id}/deactivate")
    def deactivate_style(style_id: str):
        try:
            repository.deactivate_style_template(style_id)
            return repository.get_style_template(style_id).to_dict()
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/assets/styles/{style_id}/copy")
    def copy_style(style_id: str):
        from csboard.application.context import utc_now
        import uuid

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
        from csboard.application.context import utc_now

        if not file.filename:
            return domain_error_response(DomainError("VALIDATION_ERROR", "缺少文件名"), status_code=400)

        safe_name = Path(file.filename).name
        if safe_name != file.filename or ".." in file.filename:
            return domain_error_response(DomainError("VALIDATION_ERROR", "文件名不合法"), status_code=400)

        content = bytearray()
        while chunk := await file.read(8192):
            content.extend(chunk)
            if len(content) > ASSET_UPLOAD_MAX_BYTES:
                return domain_error_response(DomainError("VALIDATION_ERROR", "文件大小超过 100MB 限制"), status_code=400)

        asset = repository.save_asset(
            file_bytes=bytes(content),
            original_name=safe_name,
            mime_type=file.content_type or "application/octet-stream",
        )
        return asset.to_dict()

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
        return {"items": [v.to_dict() for v in voices], "total": len(voices)}

    @router.post("/api/v1/assets/voices")
    def create_voice(payload: dict[str, Any]):
        name = payload.get("name", "")
        duration_ms = payload.get("duration_ms", 0)
        sample_rate = payload.get("sample_rate", 0)
        channels = payload.get("channels", 1)
        fmt = payload.get("format", "wav")

        if duration_ms < 0 or sample_rate < 0 or channels < 0:
            return domain_error_response(DomainError("VALIDATION_ERROR", "数值参数不能为负"), status_code=400)

        voice = repository.create_voice_asset(name, duration_ms, sample_rate, channels, fmt)
        return voice.to_dict()

    @router.get("/api/v1/assets/voices/{voice_id}")
    def get_voice(voice_id: str):
        try:
            voice = repository.get_voice_asset(voice_id)
            return voice.to_dict()
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.patch("/api/v1/assets/voices/{voice_id}")
    def patch_voice(voice_id: str, payload: dict[str, Any]):
        try:
            voice = repository.get_voice_asset(voice_id)
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

        if "name" in payload:
            voice.name = payload["name"]

        meta_path = repository._voice_meta_path(voice_id)
        import json
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        if "name" in payload:
            data["name"] = payload["name"]
        meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return repository.get_voice_asset(voice_id).to_dict()

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
            return repository.get_voice_asset(voice_id).to_dict()
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.post("/api/v1/assets/voices/{voice_id}/deactivate")
    def deactivate_voice(voice_id: str):
        try:
            repository.deactivate_voice_asset(voice_id)
            return repository.get_voice_asset(voice_id).to_dict()
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    @router.get("/api/v1/assets/voices/{voice_id}/content")
    def get_voice_content(voice_id: str, request: Request):
        try:
            voice = repository.get_voice_asset(voice_id)
            content = repository.get_voice_content(voice_id)
            media_type = f"audio/{voice.format}" if voice.format else "audio/wav"

            range_header = request.headers.get("range")
            if range_header:
                import re
                match = re.match(r"bytes=(\d+)-(\d*)", range_header)
                if match:
                    start = int(match.group(1))
                    end = int(match.group(2)) if match.group(2) else len(content) - 1
                    end = min(end, len(content) - 1)
                    chunk = content[start:end + 1]
                    return Response(
                        content=chunk,
                        media_type=media_type,
                        status_code=206,
                        headers={
                            "Content-Range": f"bytes {start}-{end}/{len(content)}",
                            "Accept-Ranges": "bytes",
                            "Content-Length": str(len(chunk)),
                        },
                    )

            return Response(
                content=content,
                media_type=media_type,
                headers={
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(len(content)),
                },
            )
        except NotFoundError as exc:
            return domain_error_response(exc, status_code=404)

    return router
