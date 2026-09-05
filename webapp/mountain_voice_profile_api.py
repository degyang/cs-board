"""Provider-neutral voice profile metadata API."""

from pathlib import Path

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse

from csboard.adapters.filesystem.service_registry import FilesystemServiceRegistry
from csboard.application.voice_profiles import VoiceProfileCatalog
from csboard.domain.errors import NotFoundError


def mountain_voice_profile_router(registry: FilesystemServiceRegistry, data_dir: Path, provider_factory=None) -> APIRouter:
    router = APIRouter()
    catalog = VoiceProfileCatalog(registry, data_dir)

    @router.get("/api/v1/voice-profiles")
    def list_voice_profiles(provider_id: str | None = Query(None)):
        snapshot = catalog.snapshot()
        items = [item for item in snapshot["profiles"] if provider_id is None or item.get("provider_id") == provider_id]
        return {"items": items, "total": len(items), "capabilities": snapshot["capabilities"]}

    @router.post("/api/v1/voice-profiles")
    def create_voice_profile(payload: dict = Body(...)):
        try:
            return catalog.create_profile(payload)
        except (KeyError, ValueError, NotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.patch("/api/v1/voice-profiles/{profile_id}")
    def update_voice_profile(profile_id: str, payload: dict = Body(...)):
        try:
            return catalog.update_profile(profile_id, payload)
        except (KeyError, ValueError, NotFoundError) as exc:
            code = str(exc) if str(exc).startswith("VOICE_") else str(exc)
            raise HTTPException(status_code=400, detail=code) from exc

    @router.post("/api/v1/voice-profiles/{profile_id}/preview")
    def preview_voice_profile(profile_id: str, payload: dict = Body(default_factory=dict)):
        if provider_factory is None:
            raise HTTPException(status_code=503, detail="VOICE_PREVIEW_UNAVAILABLE")
        try:
            return catalog.preview(profile_id, provider_factory, payload.get("text"))
        except Exception as exc:
            code = str(exc) if str(exc).startswith("VOICE_") else "VOICE_PREVIEW_FAILED"
            raise HTTPException(status_code=400, detail=code) from exc

    @router.get("/api/v1/voice-profiles/{profile_id}/preview")
    def get_voice_profile_preview(profile_id: str):
        try:
            path = catalog.preview_path(profile_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="VOICE_PREVIEW_NOT_FOUND") from exc
        if not path.is_file():
            raise HTTPException(status_code=404, detail="VOICE_PREVIEW_NOT_FOUND")
        return FileResponse(path, media_type="audio/wav")

    @router.get("/api/v1/voice-style-profiles")
    def list_voice_style_profiles(provider_id: str | None = Query(None)):
        snapshot = catalog.snapshot()
        items = [item for item in snapshot["styles"] if provider_id is None or item.get("provider_id") == provider_id]
        return {"items": items, "total": len(items), "capabilities": snapshot["capabilities"]}

    @router.post("/api/v1/voice-style-profiles")
    def create_voice_style_profile(payload: dict = Body(...)):
        try:
            return catalog.create_style(payload)
        except (KeyError, ValueError, NotFoundError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
