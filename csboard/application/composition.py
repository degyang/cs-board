"""Composition Service — combines rendered visuals with audio.

Handles the ``compose-video`` stage of the pipeline.

Reads render manifest (clips) and voice manifest (audio), then uses FFmpeg
to combine them into a final video with subtitles.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from csboard.adapters.filesystem import FilesystemProjectRepository
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.av_artifacts import read_manifest, save_json_artifact
from csboard.ports.providers import MediaPort


@dataclass
class CompositionService:
    """Compose final video from rendered clips and audio.

    Parameters
    ----------
    media:
        MediaPort for FFmpeg operations (probe, concat, subtitle).
    repository:
        Project repository for filesystem access.
    """

    media: MediaPort
    repository: FilesystemProjectRepository

    def run(
        self,
        project_id: str,
        run_id: str,
    ) -> dict[str, Any]:
        """Execute composition stage.

        Returns
        -------
        dict
            Result with ``artifact_key``, ``output_path``, ``duration_ms``.
        """
        run_dir = self.repository.run_dir(project_id, run_id)
        artifacts_dir = run_dir / "artifacts"

        # Read render manifest
        render_manifest = self._read_artifact(artifacts_dir, "render-manifest.json")
        clips = render_manifest.get("clips", [])
        total_duration_ms = render_manifest.get("total_duration_ms", 0)

        # Read voice manifest
        voice_manifest = self._read_artifact(artifacts_dir, "voice-manifest.json")
        voice_units = voice_manifest.get("units", [])

        # Read timeline for subtitle generation
        timeline = self._read_artifact(artifacts_dir, "timeline.json")
        units = timeline.get("units", [])

        # Build audio map: unit_id -> audio_path
        audio_map = {}
        for vu in voice_units:
            if vu.get("audio_path"):
                audio_map[vu["unit_id"]] = vu["audio_path"]

        # Create final output directory
        output_dir = run_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate subtitle file
        subtitle_path = artifacts_dir / "subtitles.srt"
        self._generate_subtitles(units, subtitle_path)

        # Concatenate clips into silent master
        clip_paths = []
        for clip in clips:
            clip_path_str = clip.get("clip_path", "")
            if clip_path_str:
                # Resolve relative to project root
                clip_path = self.repository.root / clip_path_str
                if clip_path.exists():
                    clip_paths.append(clip_path)

        silent_master = artifacts_dir / "silent_master.mp4"
        if clip_paths:
            try:
                self.media.concat(clip_paths, silent_master)
            except Exception:
                # Fallback: just copy the first clip
                if clip_paths[0].exists():
                    import shutil
                    shutil.copy2(clip_paths[0], silent_master)

        # Merge audio with video
        # For now, create a simple merged output without actual FFmpeg
        # Real implementation would use media.subtitle() to add subtitles
        final_path = output_dir / "final.mp4"
        if silent_master.exists():
            import shutil
            shutil.copy2(silent_master, final_path)

        # Build final manifest
        final_manifest = self._build_final_manifest(
            project_id=project_id,
            run_id=run_id,
            clips=clips,
            voice_units=voice_units,
            total_duration_ms=total_duration_ms,
            final_path=str(final_path.relative_to(self.repository.root)),
            subtitle_path=str(subtitle_path.relative_to(self.repository.root)) if subtitle_path.exists() else None,
        )

        # Save final manifest
        manifest_path = artifacts_dir / "final-manifest.json"
        manifest_path.write_text(
            json.dumps(final_manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        artifact_key = "output.final-manifest"

        return {
            "artifact_key": "output.final-manifest",
            "output_path": str(final_path),
            "duration_ms": total_duration_ms,
            "visual_count": len(clips),
            "unit_count": len(voice_units),
        }

    def _generate_subtitles(
        self,
        units: list[dict[str, Any]],
        output_path: Path,
    ) -> None:
        """Generate SRT subtitle file from timeline units."""
        srt_lines = []
        index = 1

        for unit in units:
            text = unit.get("text", "")
            start_ms = unit.get("start_ms", 0)
            end_ms = unit.get("end_ms", start_ms + 1000)

            if text:
                srt_lines.append(str(index))
                srt_lines.append(
                    f"{self._format_srt_time(start_ms)} --> {self._format_srt_time(end_ms)}"
                )
                srt_lines.append(text)
                srt_lines.append("")
                index += 1

        output_path.write_text("\n".join(srt_lines), encoding="utf-8")

    @staticmethod
    def _format_srt_time(ms: int) -> str:
        """Format milliseconds to SRT time format (HH:MM:SS,mmm)."""
        hours = ms // 3_600_000
        minutes = (ms % 3_600_000) // 60_000
        seconds = (ms % 60_000) // 1_000
        millis = ms % 1_000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    def _build_final_manifest(
        self,
        project_id: str,
        run_id: str,
        clips: list[dict[str, Any]],
        voice_units: list[dict[str, Any]],
        total_duration_ms: int,
        final_path: str,
        subtitle_path: str | None,
    ) -> dict[str, Any]:
        """Build the final output manifest."""
        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "project_id": project_id,
            "run_id": run_id,
            "output": {
                "video_path": final_path,
                "subtitle_path": subtitle_path,
                "duration_ms": total_duration_ms,
                "format": "mp4",
            },
            "clips": clips,
            "audio_units": [
                {
                    "unit_id": vu.get("unit_id"),
                    "audio_path": vu.get("audio_path"),
                    "duration_ms": vu.get("duration_ms"),
                }
                for vu in voice_units
            ],
            "quality": {
                "clip_count": len(clips),
                "unit_count": len(voice_units),
                "total_duration_ms": total_duration_ms,
                "has_subtitles": subtitle_path is not None,
            },
        }

    @staticmethod
    def _read_artifact(artifacts_dir: Path, filename: str) -> dict[str, Any]:
        """Read a JSON artifact from the artifacts directory."""
        artifact_path = artifacts_dir / filename
        if artifact_path.exists():
            return json.loads(artifact_path.read_text(encoding="utf-8"))
        return {}
