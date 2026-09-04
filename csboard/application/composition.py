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

from csboard.adapters.filesystem import FilesystemTaskRepository
from csboard.adapters.observability import JsonlTelemetry
from csboard.application.av_artifacts import json_bytes
from csboard.adapters.filesystem import FilesystemArtifactStore
from csboard.ports.providers import MediaPort


def final_manifest_document(
    task_id: str, run_id: str, timeline: dict[str, Any], render: dict[str, Any], duration_ms: int,
) -> dict[str, Any]:
    """Compatibility validator used by the pre-existing contract test."""
    expected = sum(int(item.get("duration_ms", 0)) for item in timeline.get("units", []))
    actual = sum(int(item.get("duration_ms", 0)) for item in render.get("clips", []))
    return {
        "task_id": task_id, "run_id": run_id, "duration_ms": duration_ms,
        "validation": {"passed": expected == actual == duration_ms, "expected_ms": expected, "actual_ms": actual},
    }


def require_valid_final(manifest: dict[str, Any]) -> dict[str, Any]:
    if not manifest.get("validation", {}).get("passed"):
        raise ValueError("禁止报告无效音画合成结果")
    return manifest


@dataclass
class CompositionService:
    """Compose final video from rendered clips and audio.

    Parameters
    ----------
    media:
        MediaPort for FFmpeg operations (probe, concat, subtitle).
    repository:
        Task repository for filesystem access.
    """

    media: MediaPort
    repository: FilesystemTaskRepository

    def run(
        self,
        task_id: str,
        run_id: str,
    ) -> dict[str, Any]:
        """Execute composition stage.

        Returns
        -------
        dict
            Result with ``artifact_key``, ``output_path``, ``duration_ms``.
        """
        run_dir = self.repository.run_dir(task_id, run_id)
        artifacts_dir = run_dir / "artifacts"
        artifacts = FilesystemArtifactStore(self.repository)

        # Read by logical artifact key.  Producers own their physical layout;
        # consumers must never reconstruct paths from file names.
        render_manifest = self._read_artifact(artifacts, task_id, run_id, "render.manifest")
        if not render_manifest:
            raise ValueError("请先运行 render-visuals 生成 render.manifest")
        clips = render_manifest.get("clips", [])
        total_duration_ms = render_manifest.get("total_duration_ms", 0)

        voice_manifest = self._read_artifact(artifacts, task_id, run_id, "audio.voice-manifest")
        voice_units = voice_manifest.get("voices", [])
        if not voice_units:
            raise ValueError("请先运行 clone-voice 生成 audio.voice-manifest")

        timeline = self._read_artifact(artifacts, task_id, run_id, "timing.timeline")
        units = timeline.get("units", [])
        if not units:
            raise ValueError("请先运行 clone-voice 生成 timing.timeline")
        av_plan = self._read_artifact(artifacts, task_id, run_id, "planning.av-plan")
        text_by_unit = {item.get("unit_id"): item.get("text", "") for item in av_plan.get("voice_units", [])}
        subtitle_units: list[dict[str, Any]] = []
        cursor_ms = 0
        for unit in units:
            duration_ms = int(unit.get("duration_ms", 0))
            subtitle_units.append({
                "text": text_by_unit.get(unit.get("unit_id"), unit.get("text", "")),
                "start_ms": cursor_ms,
                "end_ms": cursor_ms + duration_ms,
            })
            cursor_ms += duration_ms

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
        self._generate_subtitles(subtitle_units, subtitle_path)

        # Concatenate visual clips and narration audio with FFmpeg.  A final
        # result is never considered successful without both streams.
        clip_paths: list[Path] = []
        for clip in clips:
            clip_path_str = clip.get("clip_path", "")
            if clip_path_str:
                clip_path = run_dir / clip_path_str
                if clip_path.exists():
                    clip_paths.append(clip_path)
        if not clip_paths:
            raise ValueError("render.manifest 中没有可用的视频片段")

        audio_paths: list[Path] = []
        for voice in voice_units:
            audio_path = voice.get("audio_path", "")
            if audio_path:
                path = run_dir / str(audio_path).removeprefix("artifacts/")
                # Voice manifests use an artifact-relative path.
                if not path.exists():
                    path = run_dir / "artifacts" / str(audio_path).removeprefix("artifacts/")
                if path.exists():
                    audio_paths.append(path)
        if not audio_paths:
            raise ValueError("audio.voice-manifest 中没有可用的语音文件")

        silent_master = output_dir / "visuals.mp4"
        narration = output_dir / "narration.wav"
        final_path = output_dir / "final.mp4"
        muxed_path = output_dir / "muxed.mp4"
        self.media.concat(clip_paths, silent_master)
        self.media.concat(audio_paths, narration)
        self.media.mux_audio(silent_master, narration, muxed_path)
        self.media.subtitle(muxed_path, subtitle_path, final_path)
        if not final_path.exists() or final_path.stat().st_size == 0:
            raise RuntimeError("FFmpeg 未生成最终视频")
        probe = self.media.probe(final_path)
        if probe.duration_ms <= 0 or not probe.codec:
            raise RuntimeError("最终视频校验失败：未检测到有效视频流")

        expected_ms = sum(
            int(item.get("duration_ms") or (int(item.get("end_ms", 0)) - int(item.get("start_ms", 0))))
            for item in units
        )
        rendered_ms = sum(int(item.get("duration_ms", 0)) for item in clips)
        voiced_ms = sum(int(item.get("duration_ms", 0)) for item in voice_units)
        tolerance_ms = max(250, int(expected_ms * 0.02))
        validation = {
            "passed": (
                expected_ms > 0
                and expected_ms == rendered_ms == voiced_ms
                and abs(probe.duration_ms - expected_ms) <= tolerance_ms
                and bool(probe.codec)
                and probe.sample_rate > 0
                and probe.channels > 0
            ),
            "expected_ms": expected_ms,
            "rendered_ms": rendered_ms,
            "voiced_ms": voiced_ms,
            "actual_ms": probe.duration_ms,
            "tolerance_ms": tolerance_ms,
            "video_codec": probe.codec,
            "audio_sample_rate": probe.sample_rate,
            "audio_channels": probe.channels,
        }
        if not validation["passed"]:
            raise RuntimeError("最终视频校验失败：音画流或时长不符合契约")

        # Build final manifest
        final_manifest = self._build_final_manifest(
            task_id=task_id,
            run_id=run_id,
            clips=clips,
            voice_units=voice_units,
            total_duration_ms=total_duration_ms,
            final_path=str(final_path.relative_to(self.repository.root)),
            subtitle_path=str(subtitle_path.relative_to(self.repository.root)) if subtitle_path.exists() else None,
            validation=validation,
        )

        manifest_ref = artifacts.commit_bytes(
            task_id, run_id, "output.final-manifest", "output/final-manifest.json",
            json_bytes(final_manifest), "compose-video",
        )
        artifacts.commit_bytes(
            task_id, run_id, "output.final-video", "output/final.mp4",
            final_path.read_bytes(), "compose-video",
        )

        return {
            "artifact_key": manifest_ref.artifact_key,
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
        task_id: str,
        run_id: str,
        clips: list[dict[str, Any]],
        voice_units: list[dict[str, Any]],
        total_duration_ms: int,
        final_path: str,
        subtitle_path: str | None,
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the final output manifest."""
        return {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "task_id": task_id,
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
            "validation": validation,
        }

    def _read_artifact(
        self, artifacts: FilesystemArtifactStore, task_id: str, run_id: str, key: str,
    ) -> dict[str, Any]:
        ref = artifacts.get(task_id, run_id, key)
        if not ref:
            return {}
        path = self.repository.run_dir(task_id, run_id) / "artifacts" / ref["relative_path"]
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
