"""Mountain Asset API — /api/v1/assets 端点。

资产管理：风格模板、资产上传、语音资产。
不依赖 legacy 模块。
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from csboard.adapters.filesystem.asset_repository import FilesystemAssetRepository
from csboard.application.context import utc_now
from csboard.domain.asset_ref import AssetRef
from csboard.domain.errors import DomainError, NotFoundError
from csboard.domain.style_template import StyleTemplate
from csboard.domain.voice_asset import VoiceAsset


def mountain_asset_router(data_dir: Path) -> APIRouter:
    """创建 /api/v1/assets 路由器。"""
    repository = FilesystemAssetRepository(data_dir)
    router = APIRouter(prefix="/api/v1/assets", tags=["mountain-assets"])

    # ── Style Templates ────────────────────────────────────────────

    @router.get("/styles")
    def list_styles(kind: str | None = None) -> dict[str, Any]:
        """列出风格模板。"""
        templates = repository.list_style_templates(kind=kind)
        return {
            "items": [t.to_dict() for t in templates],
            "total": len(templates),
        }

    @router.get("/styles/{template_id}")
    def get_style(template_id: str) -> dict[str, Any]:
        """获取风格模板详情。"""
        try:
            template = repository.get_style_template(template_id)
            return template.to_dict()
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @router.post("/styles")
    def create_style(
        name: str = Form(...),
        prompt_text: str = Form(...),
        negative_prompt: str = Form(""),
        tags: str = Form("[]"),
        copy_from: str = Form(""),
    ) -> dict[str, Any]:
        """创建 custom 风格模板。可从 preset 复制。"""
        try:
            tag_list = json.loads(tags) if tags else []
        except json.JSONDecodeError:
            tag_list = []

        now = utc_now()
        template_id = uuid.uuid4().hex[:16]

        if copy_from:
            # 从已有模板复制
            try:
                source = repository.get_style_template(copy_from)
            except NotFoundError as exc:
                raise HTTPException(status_code=404, detail=str(exc))
            template = source.copy_to_custom(template_id, now)
            template.name = name or template.name
            template.prompt_text = prompt_text or template.prompt_text
            template.negative_prompt = negative_prompt or template.negative_prompt
            template.tags = tag_list or template.tags
        else:
            template = StyleTemplate(
                template_id=template_id,
                revision=1,
                name=name,
                kind="custom",
                prompt_text=prompt_text,
                negative_prompt=negative_prompt,
                tags=tag_list,
                is_active=True,
                created_at=now,
                updated_at=now,
            )

        try:
            repository.save_style_template(template)
            return template.to_dict()
        except DomainError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @router.patch("/styles/{template_id}")
    def update_style(
        template_id: str,
        name: str = Form(""),
        prompt_text: str = Form(""),
        negative_prompt: str = Form(""),
        tags: str = Form(""),
    ) -> dict[str, Any]:
        """更新 custom 风格模板。"""
        try:
            template = repository.get_style_template(template_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

        if template.kind == "preset":
            raise HTTPException(status_code=422, detail="preset 风格禁止修改")

        if name:
            template.name = name
        if prompt_text:
            template.prompt_text = prompt_text
        if negative_prompt:
            template.negative_prompt = negative_prompt
        if tags:
            try:
                template.tags = json.loads(tags)
            except json.JSONDecodeError:
                pass

        try:
            repository.save_style_template(template)
            return template.to_dict()
        except DomainError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @router.delete("/styles/{template_id}")
    def deactivate_style(template_id: str) -> dict[str, Any]:
        """停用 custom 风格模板（软删除）。"""
        try:
            repository.deactivate_style_template(template_id)
            return {"ok": True}
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except DomainError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    # ── Asset Upload ───────────────────────────────────────────────

    @router.post("/upload")
    async def upload_asset(
        file: UploadFile = File(...),
    ) -> dict[str, Any]:
        """暂存上传（图片/音频/文档）。"""
        content = await file.read()
        if not content:
            raise HTTPException(status_code=422, detail="文件内容为空")

        mime_type = file.content_type or "application/octet-stream"
        original_name = file.filename or "unnamed"

        try:
            ref = repository.save_asset(content, original_name, mime_type)
            return ref.to_dict()
        except DomainError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @router.get("/blobs/{asset_id}")
    def get_asset(asset_id: str) -> Response:
        """读取资产文件内容。"""
        try:
            ref = repository.get_asset(asset_id)
            data = repository.read_asset_bytes(asset_id)
            return Response(content=data, media_type=ref.mime_type)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except DomainError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    # ── Voice Assets ───────────────────────────────────────────────

    @router.post("/voices/upload")
    async def upload_voice(
        file: UploadFile = File(...),
        name: str = Form(""),
    ) -> dict[str, Any]:
        """语音上传。"""
        content = await file.read()
        if not content:
            raise HTTPException(status_code=422, detail="文件内容为空")

        original_name = file.filename or "unnamed.wav"
        voice_name = name or original_name

        # 检测格式
        if original_name.lower().endswith(".mp3"):
            audio_format = "mp3"
        else:
            audio_format = "wav"

        # 使用 ffprobe 校验
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration,sample_rate,channels", "-of", "json", tmp_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode:
                raise HTTPException(status_code=422, detail="音频文件格式无效")

            probe_data = json.loads(result.stdout)
            duration_ms = int(float(probe_data.get("format", {}).get("duration", 0)) * 1000)
            sample_rate = int(probe_data.get("format", {}).get("sample_rate", 24000))
            channels = int(probe_data.get("format", {}).get("channels", 1))
        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=f"音频探测失败: {exc}")
        finally:
            import os
            os.unlink(tmp_path)

        try:
            asset = repository.save_voice_asset(
                content, voice_name, duration_ms, sample_rate, channels, audio_format
            )
            return asset.to_dict()
        except DomainError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @router.get("/voices")
    def list_voices() -> dict[str, Any]:
        """列出语音资产。"""
        voices = repository.list_voice_assets()
        return {
            "items": [v.to_dict() for v in voices],
            "total": len(voices),
        }

    @router.get("/voices/{voice_id}")
    def get_voice(voice_id: str) -> dict[str, Any]:
        """获取语音资产详情。"""
        try:
            voice = repository.get_voice_asset(voice_id)
            return voice.to_dict()
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    @router.delete("/voices/{voice_id}")
    def deactivate_voice(voice_id: str) -> dict[str, Any]:
        """停用语音资产（软删除）。"""
        try:
            repository.deactivate_voice_asset(voice_id)
            return {"ok": True}
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

    return router
