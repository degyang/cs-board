from __future__ import annotations

import hashlib
from typing import Any

from csboard.application.av_artifacts import _metadata
from csboard.domain.enums import Engine


def illustration_manifest_document(project_id: str, run_id: str, images: list[dict[str, Any]], profile: str, model: str) -> dict[str, Any]:
    """Build the stable record consumed by renderers; source and final stay distinct."""
    illustrations = []
    for image in images:
        payload = bytes(image["payload"])
        illustrations.append({
            "visual_id": image["visual_id"],
            "source_image_path": image["source_image_path"],
            "final_image_path": image["final_image_path"],
            "sha256": f"sha256:{hashlib.sha256(payload).hexdigest()}",
            "width": int(image.get("width", 1920)), "height": int(image.get("height", 1080)),
            "profile": profile, "model": model, "attempt": int(image.get("attempt", 1)),
        })
    return {**_metadata("illustration-manifest", "illustrations.manifest", project_id, run_id, "generate-illustrations", Engine.WHITEBOARD), "illustrations": illustrations}
