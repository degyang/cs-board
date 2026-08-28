from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from csboard.domain.models import ArtifactRef
from csboard.domain.validation import validate_relative_path

from .repository import FilesystemProjectRepository


DOWNSTREAM_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "planning.av-plan": (
        "audio.voice-manifest",
        "timing.timeline",
        "planning.storyboard",
        "illustrations.manifest",
        "render.manifest",
        "output.final-manifest",
    ),
    "audio.voice-manifest": ("timing.timeline", "render.manifest", "output.final-manifest"),
    "timing.timeline": ("render.manifest", "output.final-manifest"),
    "planning.storyboard": ("illustrations.manifest", "render.manifest", "output.final-manifest"),
    "illustrations.manifest": ("render.manifest", "output.final-manifest"),
    "render.manifest": ("output.final-manifest",),
}


class FilesystemArtifactStore:
    """Atomically stores run artifacts and tracks their invalidation state."""

    def __init__(self, repository: FilesystemProjectRepository) -> None:
        self.repository = repository

    def commit_bytes(
        self,
        project_id: str,
        run_id: str,
        artifact_key: str,
        relative_path: str,
        payload: bytes,
        producer_stage: str,
    ) -> ArtifactRef:
        validate_relative_path(relative_path)
        run_dir = self.repository.run_dir(project_id, run_id)
        self.repository.get_run(project_id, run_id)
        target = run_dir / "artifacts" / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(f"{target.suffix}.{os.getpid()}.partial")
        with temporary.open("wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)

        reference = ArtifactRef(
            artifact_key=artifact_key,
            relative_path=relative_path,
            sha256=hashlib.sha256(payload).hexdigest(),
            size_bytes=len(payload),
            producer_stage=producer_stage,
        )
        with self.repository.project_lock(project_id):
            index = self._read_index(run_dir)
            index["artifacts"][artifact_key] = reference.to_dict()
            self._write_index(run_dir, index)
        return reference

    def get(self, project_id: str, run_id: str, artifact_key: str) -> dict[str, Any] | None:
        index = self._read_index(self.repository.run_dir(project_id, run_id))
        return index["artifacts"].get(artifact_key)

    def invalidate_from(self, project_id: str, run_id: str, artifact_key: str, reason: str) -> list[str]:
        """Mark only known downstream output as stale; source output stays usable."""
        run_dir = self.repository.run_dir(project_id, run_id)
        self.repository.get_run(project_id, run_id)
        invalidated: list[str] = []
        with self.repository.project_lock(project_id):
            index = self._read_index(run_dir)
            for dependent in DOWNSTREAM_ARTIFACTS.get(artifact_key, ()):
                item = index["artifacts"].get(dependent)
                if item is not None and item.get("status") != "stale":
                    item["status"] = "stale"
                    item["invalidation_reason"] = reason
                    invalidated.append(dependent)
            self._write_index(run_dir, index)
        return invalidated

    def _read_index(self, run_dir: Path) -> dict[str, Any]:
        return self.repository.read_json(run_dir / "artifacts" / "index.json")

    def _write_index(self, run_dir: Path, value: dict[str, Any]) -> None:
        self.repository.write_json(run_dir / "artifacts" / "index.json", value)
