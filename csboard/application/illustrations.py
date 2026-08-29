"""Illustration generation service.

Generates images for each Visual Item based on the storyboard.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from csboard.adapters.filesystem import FilesystemArtifactStore, FilesystemProjectRepository
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.av_artifacts import json_bytes, illustration_manifest_document
from csboard.domain.enums import Engine, StageStatus
from csboard.domain.models import StageState
from csboard.domain.provider_types import ImageGenerationRequest
from csboard.ports.providers import ImageModelPort


@dataclass
class IllustrationService:
    """Generate illustrations for each Visual Item.

    Parameters
    ----------
    image_model:
        Image model port for generating images.
    repository:
        Project repository for reading/writing artifacts.
    """

    image_model: ImageModelPort
    repository: FilesystemProjectRepository
    artifacts: FilesystemArtifactStore = field(init=False)
    telemetry: JsonlTelemetry = field(init=False)

    def __post_init__(self) -> None:
        self.artifacts = FilesystemArtifactStore(self.repository)
        self.telemetry = JsonlTelemetry(self.repository)

    def run(
        self,
        project_id: str,
        run_id: str,
        engine: Engine = Engine.WHITEBOARD,
        visual_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate illustrations for Visual Items.

        Parameters
        ----------
        project_id:
            Project identifier.
        run_id:
            Run identifier.
        engine:
            Visual engine (whiteboard, etc.).
        visual_id:
            If specified, only generate for this visual (for retry).

        Returns
        -------
        dict with keys: illustrations, image_count
        """
        # Read storyboard
        storyboard = self._read_artifact(project_id, run_id, "planning.storyboard")
        if not storyboard:
            raise ValueError("请先运行 plan-storyboard 生成 storyboard")

        # Filter to specific visual if retrying
        visuals = storyboard.get("visuals", [])
        if visual_id:
            visuals = [v for v in visuals if v["visual_id"] == visual_id]
            if not visuals:
                raise ValueError(f"Visual {visual_id} 不存在于 storyboard 中")

        # Generate images
        run_dir = self.repository.run_dir(project_id, run_id)
        images_dir = run_dir / "media" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        illustrations: list[dict[str, Any]] = []
        for visual in visuals:
            illustration = self._generate_single(
                project_id, run_id, visual, images_dir, engine
            )
            illustrations.append(illustration)

        # Build manifest document
        doc = illustration_manifest_document(project_id, run_id, illustrations, engine)

        # Commit artifact
        artifact = self.artifacts.commit_bytes(
            project_id, run_id,
            "illustrations.manifest",
            "planning/illustration-manifest.json",
            json_bytes(doc),
            "generate-illustrations",
        )

        return {
            "illustrations": doc,
            "image_count": len(illustrations),
            "artifact_key": artifact.artifact_key,
        }

    def _generate_single(
        self,
        project_id: str,
        run_id: str,
        visual: dict[str, Any],
        images_dir: Path,
        engine: Engine,
    ) -> dict[str, Any]:
        """Generate a single illustration."""
        visual_id = visual["visual_id"]
        prompt = visual.get("prompt", "")
        negative_prompt = visual.get("negative_prompt", "")

        request = ImageGenerationRequest(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=1920 if engine == Engine.WHITEBOARD else 1024,
            height=1080 if engine == Engine.WHITEBOARD else 1024,
        )

        result = self.image_model.generate(request)

        if not result.images:
            raise RuntimeError(f"图片生成失败: {visual_id}")

        # Save image
        image_data = result.images[0]
        image_filename = f"{visual_id}.png"
        image_path = images_dir / image_filename
        image_path.write_bytes(image_data)

        # Compute hash
        sha256 = hashlib.sha256(image_data).hexdigest()

        return {
            "visual_id": visual_id,
            "unit_id": visual.get("unit_id", ""),
            "image_path": f"runs/{run_id}/media/images/{image_filename}",
            "sha256": f"sha256:{sha256}",
            "width": request.width,
            "height": request.height,
            "model": result.model or "unknown",
            "attempt": 1,
            "source_prompt": prompt[:200],  # Truncated for safety
        }

    def _read_artifact(self, project_id: str, run_id: str, key: str) -> dict[str, Any] | None:
        """Read an artifact by key, returning parsed JSON or None."""
        ref = self.artifacts.get(project_id, run_id, key)
        if not ref:
            return None
        path = self.repository.run_dir(project_id, run_id) / "artifacts" / ref["relative_path"]
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
